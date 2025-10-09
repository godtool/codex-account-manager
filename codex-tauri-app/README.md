# Codex 账号管理器 - Tauri 桌面版

这是 Codex 账号管理器的 Tauri 2.0 桌面应用版本，所有逻辑都在前端 JavaScript 实现。

## 快速开始

### 1. 安装依赖

```bash
cd codex-tauri-app
npm install
```

### 2. 运行开发版本

```bash
npm run dev
```

### 3. 构建应用

```bash
npm run build
```

构建后的应用在 `src-tauri/target/release/bundle/` 目录下。

## 功能特性

- ✅ 保存当前账号配置
- ✅ 切换账号
- ✅ 删除账号
- ✅ 添加新账号配置
- ✅ 查看用量信息（从 ~/.codex/sessions 解析）
- ✅ 30天用量缓存

## 技术栈

- **Tauri 2.0** - 跨平台桌面应用框架
- **纯前端JavaScript** - 所有业务逻辑
- **Rust** - 最小化后端

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
