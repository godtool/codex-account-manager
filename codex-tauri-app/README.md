# Codex 账号管理器 - Tauri 桌面版

这是 Codex 账号管理器的 Tauri 2.0 桌面应用版本，所有逻辑都在前端 JavaScript 实现。

## 快速开始

### 前置要求

**必须安装：**
1. **Node.js** (推荐 18+)
2. **Rust** - [安装指南](https://www.rust-lang.org/tools/install)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

**系统依赖：**
- **macOS**: 安装 Xcode Command Line Tools
  ```bash
  xcode-select --install
  ```
- **Linux (Ubuntu/Debian)**: 
  ```bash
  sudo apt update
  sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget file libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
  ```
- **Windows**: 需要 Microsoft Visual Studio C++ Build Tools

### 1. 安装依赖

```bash
cd codex-tauri-app
npm install
```

### 2. 运行开发版本

```bash
npm run tauri dev
```

### 3. 构建应用

```bash
npm run tauri build
```

构建后的应用在 `src-tauri/target/release/bundle/` 目录下。

## 功能特性

- ✅ 保存当前账号配置
- ✅ 切换账号
- ✅ 删除账号
- ✅ 查看用量信息（从 ~/.codex/sessions 解析）
- ✅ 30天用量缓存

## 技术栈

- **Tauri 2.0** - 跨平台桌面应用框架
- **纯前端JavaScript** - 所有业务逻辑
- **Rust** - 最小化后端

## macOS 安装说明 ⚠️

由于应用未经过苹果官方签名，macOS 用户首次运行可能会遇到「应用已损坏」或「无法打开」的提示。

### 快速解决方法（推荐）

1. 打开终端（Terminal）
2. 输入 `xattr -cr ` （注意 cr 后面有个空格）
3. 把应用图标拖拽到终端窗口
4. 按回车执行

执行完成后，应用就可以正常打开了。


## 项目结构

```
codex-tauri-app/
├── src/
│   ├── index.html       # 主界面
│   ├── styles.css       # 样式
│   └── main.js          # 业务逻辑
├── src-tauri/
│   ├── Cargo.toml       # Rust配置
│   ├── tauri.conf.json  # Tauri配置
│   └── src/
│       └── lib.rs       # Rust入口
└── package.json
```

## 配置文件位置

- 系统认证文件：`~/.codex/auth.json`
- 账号配置目录：`~/.codex-account-manager/codex-config/accounts/`
- 用量缓存目录：`~/.codex-account-manager/codex-config/usage_cache/`

## 注意事项

1. 与Python版本功能完全一致
2. 支持macOS、Windows、Linux
3. 切换账号后需重启Codex应用生效
4. macOS 用户请参考上方安装说明
