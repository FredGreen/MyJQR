<template>
  <router-view />
</template>

<style>
body { margin: 0; background: #f5f6f8; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }

/* 手机端：对话框/消息框宽度自适应，主内容边距收紧 */
@media (max-width: 768px) {
  .el-dialog { width: 94% !important; margin-top: 6vh !important; }
  .el-main { padding: 12px !important; }
  .el-message-box { width: 90% !important; }
}
</style>
