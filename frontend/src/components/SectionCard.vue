<template>
  <section class="card">
    <header v-if="$slots.header" class="card-header">
      <slot name="header" />
    </header>
    <slot />
  </section>
</template>
