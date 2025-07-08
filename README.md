基于官方的小智后端源码进行的二次开发
1.在原有基础上与小智客户端建立了http和websocket连接，当温度超过阈值时，将请求通过http发送到后端，经过LLM处理后通过websocket传回小智客户端，使得小智可以说出贴合场景的提示语
(需配合经过二次开发的小智客户端使用)
2.首次clone到本地后，在main/manger-web下需要先执行命令sudo npm init,然后一直按回车，最后输入yes，可以看到目录下会生成一个package.json的文件，随后将以下内容复制到package.json中保存(保存失败是因为权限原因，给package.json最高权限就可以了)，随后执行命令sudo npm install更新，
在manager-web目录下添加三个文件
.env：
VUE_APP_TITLE=智控台

.env.development：
VUE_APP_API_BASE_URL=/xiaozhi

jsconfig.json：
{
    "compilerOptions": {
      "target": "es5",
      "module": "esnext",
      "baseUrl": "./",
      "moduleResolution": "node",
      "paths": {
        "@/*": [
          "src/*"
        ]
      },
      "lib": [
        "esnext",
        "dom",
        "dom.iterable",
        "scripthost"
      ]
    }
  }


最后执行sudo npm run serve启动程序


{
  "name": "xiaozhi",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "serve": "vue-cli-service serve",
    "build": "vue-cli-service build",
    "analyze": "cross-env ANALYZE=true vue-cli-service build"
  },
  "dependencies": {
    "core-js": "^3.41.0",
    "cross-env": "^7.0.3",
    "dotenv": "^16.5.0",
    "element-ui": "^2.15.14",
    "flyio": "^0.6.14",
    "normalize.css": "^8.0.1",
    "opus-decoder": "^0.7.7",
    "opus-recorder": "^8.0.5",
    "vue": "^2.6.14",
    "vue-axios": "^3.5.2",
    "vue-router": "^3.6.5",
    "vuex": "^3.6.2",
    "xiaozhi": "file:"
  },
  "devDependencies": {
    "@babel/plugin-syntax-dynamic-import": "^7.8.3",
    "@babel/plugin-transform-runtime": "^7.26.10",
    "@vue/cli-plugin-router": "~5.0.0",
    "@vue/cli-plugin-vuex": "~5.0.0",
    "@vue/cli-service": "~5.0.0",
    "compression-webpack-plugin": "^11.1.0",
    "sass": "^1.32.7",
    "sass-loader": "^12.0.0",
    "vue-template-compiler": "^2.6.14",
    "webpack-bundle-analyzer": "^4.10.2",
    "workbox-webpack-plugin": "^7.3.0"
  },
  "browserslist": [
    "> 1%",
    "last 2 versions",
    "not dead"
  ],
  "sideEffects": [
    "*.css",
    "*.scss",
    "*.vue"
  ]
}
