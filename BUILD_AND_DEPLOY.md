# 小红书帖子生成器 EXE 打包说明

## 一键打包

```powershell
cd C:\Github_copilot\redbook
.\build_exe.ps1
```

打包完成后产物在：

```
C:\Github_copilot\redbook\dist\小红书帖子生成器\
├── 小红书帖子生成器.exe   ← 双击运行
├── _internal\             ← Python 运行时 + 所有依赖
├── streamlit_app.py
├── app\
├── structured\
└── tests\
```

整个文件夹大约 250-350MB，直接 zip 拷贝到任何 Win10/Win11 64 位电脑即可使用，**不需要装 Python**。

## 使用方法

1. 双击 `小红书帖子生成器.exe`
2. 弹出黑色控制台，等 5-10 秒
3. 浏览器自动打开 `http://localhost:8501`
4. 在左侧栏填入千问 API Key 即可使用
5. **关闭控制台窗口 = 退出程序**

## 常见问题

### Defender 误报 / 提示"未知发布者"
- 第一次运行点 **更多信息 → 仍要运行**
- 永久解决：用代码签名证书签名 exe（年费 ~¥500）
- 团队内部用：把 exe 加入 Defender 白名单

### 浏览器没自动打开
手动访问 `http://localhost:8501`

### 端口被占用
关掉本机其他占用 8501 端口的程序，或修改 `launcher.py` 里的 `port = 8501`

### 想给完全不懂电脑的家人/同事用
- 把整个文件夹压缩成 zip 发过去
- 教他们：解压 → 双击 exe → 等浏览器自动打开 → 填一次 Key 就够了

## 部署到 Streamlit Cloud（手机访问）

让粉丝/团队从手机浏览器访问：

1. 把项目推到 GitHub（公开或私有都行）
2. 注册 https://share.streamlit.io（用 GitHub 账号登录，免费）
3. 点 **New app** → 选你的 repo → 分支 `main` → 主文件 `streamlit_app.py`
4. **Advanced settings → Secrets** 填入：
   ```toml
   DASHSCOPE_API_KEY = "sk-你的真实key"
   QWEN_MODEL = "qwen-plus"
   ```
5. 点 **Deploy**，2-3 分钟后得到公网 URL：`https://xxx.streamlit.app`
6. 手机浏览器打开 → "添加到主屏幕" → 体验等同 App

### 注意事项
- API Key **不要**硬编码到代码里，必须通过 Streamlit Secrets 配置
- Streamlit Cloud 免费版有内存上限（1GB），生成 PDF 时如果数据量大可能 OOM
- 公开 URL 谁都能访问，建议在代码里加个简单的密码门
