"""API 端到端验证脚本：验证最近的传感器替换和 MySQL 迁移后所有功能正常。"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(url, data=None, headers=None, form=False):
    headers = headers or {}
    if form:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = data.encode() if data else None
    else:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    results = []

    # 1. 健康检查
    try:
        h = get(f"{BASE}/health")
        ok = h.get("status") == "ok"
        results.append(("健康检查 /health", ok, f"status={h.get('status')}, mqtt={h.get('mqtt')}"))
    except Exception as e:
        results.append(("健康检查 /health", False, str(e)))

    # 2. 登录
    try:
        login = post(f"{BASE}/api/v1/auth/login", "username=admin&password=Admin123456", form=True)
        token = login["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        results.append(("登录 /auth/login", True, f"token_type={login['token_type']}, token_len={len(token)}"))
    except Exception as e:
        results.append(("登录 /auth/login", False, str(e)))
        return results

    # 3. 最新传感器数据（验证 co2 字段存在，soil_temp 不存在）
    try:
        latest = get(f"{BASE}/api/v1/sensors/data/latest", headers)
        has_co2 = "co2" in latest
        no_soil_temp = "soil_temp" not in latest
        ok = has_co2 and no_soil_temp
        results.append(("最新传感器数据 /sensors/data/latest", ok,
                        f"co2={latest.get('co2')}, has_co2={has_co2}, no_soil_temp={no_soil_temp}"))
    except Exception as e:
        results.append(("最新传感器数据 /sensors/data/latest", False, str(e)))

    # 4. ECharts 数据（验证 co2 系列存在）
    try:
        echarts = get(f"{BASE}/api/v1/sensors/data/echarts?limit=5", headers)
        series_names = [s["name"] for s in echarts["series"]]
        ok = "co2" in series_names and "soil_temp" not in series_names
        results.append(("ECharts 数据 /sensors/data/echarts", ok,
                        f"系列={series_names}"))
    except Exception as e:
        results.append(("ECharts 数据 /sensors/data/echarts", False, str(e)))

    # 5. 规则列表
    try:
        rules = get(f"{BASE}/api/v1/rules", headers)
        results.append(("规则列表 /rules", True, f"数量={len(rules)}"))
    except Exception as e:
        results.append(("规则列表 /rules", False, str(e)))

    # 6. 设备节点
    try:
        nodes = get(f"{BASE}/api/v1/device-nodes", headers)
        results.append(("设备节点 /device-nodes", True, f"数量={len(nodes)}"))
    except Exception as e:
        results.append(("设备节点 /device-nodes", False, str(e)))

    # 7. 上报传感器数据（验证 co2 写入 MySQL）
    try:
        payload = {
            "node_id": 1, "air_temp": 26.5, "air_humidity": 58.0,
            "soil_humidity": 45.0, "light_intensity": 350.0,
            "soil_ph": 6.8, "co2": 750.0
        }
        created = post(f"{BASE}/api/v1/sensors/data", payload, headers)
        ok = created.get("co2") == 750.0
        results.append(("上报传感器数据 /sensors/data", ok,
                        f"id={created.get('id')}, co2={created.get('co2')}"))
    except Exception as e:
        results.append(("上报传感器数据 /sensors/data", False, str(e)))

    # 8. 创建 CO2 规则（验证 co2 可作为规则指标，幂等：已存在则跳过）
    try:
        existing_rules = get(f"{BASE}/api/v1/rules", headers)
        existing_co2 = [r for r in existing_rules if r.get("metric") == "co2"]
        if existing_co2:
            r = existing_co2[0]
            results.append(("创建 CO2 规则 /rules", True,
                            f"已存在 co2 规则: id={r.get('id')}, threshold={r.get('threshold')}"))
        else:
            rule_payload = {
                "name": "高CO2开风扇", "metric": "co2", "operator": ">",
                "threshold": 1200.0, "action_component_type": "fan",
                "action": "on", "enabled": True, "description": "CO2超过1200ppm自动通风"
            }
            rule = post(f"{BASE}/api/v1/rules", rule_payload, headers)
            ok = rule.get("metric") == "co2"
            results.append(("创建 CO2 规则 /rules", ok,
                            f"id={rule.get('id')}, metric={rule.get('metric')}, threshold={rule.get('threshold')}"))
    except Exception as e:
        results.append(("创建 CO2 规则 /rules", False, str(e)))

    # 9. MCP 日志列表（验证 MCP 模块可用，/mcp/tools 需设备 token 故跳过）
    try:
        mcp_logs = get(f"{BASE}/api/v1/mcp/logs", headers)
        results.append(("MCP 日志列表 /mcp/logs", True, f"日志数量={len(mcp_logs)}"))
    except Exception as e:
        results.append(("MCP 日志列表 /mcp/logs", False, str(e)))

    # 10. 用户列表
    try:
        users = get(f"{BASE}/api/v1/users", headers)
        results.append(("用户列表 /users", True, f"数量={len(users)}"))
    except Exception as e:
        results.append(("用户列表 /users", False, str(e)))

    return results


if __name__ == "__main__":
    results = main()
    print("\n" + "=" * 70)
    print("API 端到端验证结果")
    print("=" * 70)
    passed = 0
    for name, ok, detail in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}  {name}")
        print(f"         {detail}")
        if ok:
            passed += 1
    print("=" * 70)
    print(f"总计: {passed}/{len(results)} 通过")
    if passed < len(results):
        sys.exit(1)
