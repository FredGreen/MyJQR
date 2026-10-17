<template>
  <router-view />
</template>

<style>
body { margin: 0; background: #f5f6f8; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.page { max-width: 1080px; margin: 0 auto; padding: 20px; }

/* 手机端：页面边距收紧、对话框自适应 */
@media (max-width: 768px) {
  .page { padding: 12px; }
  .el-dialog { width: 94% !important; margin-top: 6vh !important; }
}
</style>
