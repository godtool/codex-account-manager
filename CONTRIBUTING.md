# 贡献指南

感谢您对 OpenAI Codex 账号管理器项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- 🌍 翻译项目

## 🚀 快速开始

### 开发环境设置

1. **Fork 和克隆仓库**
```bash
# Fork 仓库到您的 GitHub 账户，然后克隆
git clone https://github.com/your-username/codex-account-manager.git
cd codex-account-manager
```

2. **设置开发环境**
```bash
# 确保 Python 3.6+ 已安装
python3 --version

# 安装依赖（如需要）
pip install -r requirements.txt
```

3. **测试项目**
```bash
# 运行基本测试
python3 codex_account_manager.py --help
python3 switch_account.py
```

## 🤝 如何贡献

### 报告问题 (Issues)
提交高质量的 Issue 可以帮助项目更好地发展：

- **Bug 报告**：
  - 使用清晰的标题描述问题
  - 提供详细的复现步骤
  - 包含系统环境信息（操作系统、Python 版本等）
  - 如果可能，提供错误日志或截图

- **功能请求**：
  - 描述您希望添加的功能
  - 解释为什么这个功能有用
  - 如果可能，提供实现建议

### 提交代码 (Pull Requests)

1. **创建分支**
```bash
# 从 main 分支创建新分支
git checkout -b feature/新功能名称
# 或
git checkout -b fix/修复的问题
```

2. **进行开发**
   - 保持提交消息清晰明了
   - 定期与主分支同步：`git pull origin main`

3. **提交代码**
```bash
git add .
git commit -m "简短描述修改内容"
git push origin feature/新功能名称
```

4. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写详细的 PR 描述
   - 关联相关 Issue（如果有）

## 📋 代码规范

### Python 代码风格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 4 个空格缩进
- 行长度限制在 88 字符内
- 使用有意义的变量和函数名

### 注释和文档
- **中文注释**：对关键逻辑和复杂部分使用中文注释
- **文档字符串**：为函数和类添加 docstring
- **README 更新**：如果添加新功能，请更新相关文档

### 错误处理
- 添加适当的 try-catch 块
- 提供有意义的错误消息
- 优雅地处理异常情况

### 安全考虑
- 不要在代码中硬编码敏感信息
- 验证用户输入
- 确保配置文件的安全处理

## 🧪 测试指南

### 基本测试
在提交 PR 之前，请确保：

1. **功能测试**
```bash
# 测试账号管理功能
python3 codex_account_manager.py

# 测试切换功能
python3 switch_account.py

# 测试 Web 界面
python3 codex_account_manager_web.py
```

2. **兼容性测试**
   - 在不同操作系统上测试（Windows, macOS, Linux）
   - 测试不同 Python 版本（3.6+）
   - 确保向后兼容性

3. **安全测试**
   - 验证敏感信息不会泄露
   - 测试配置文件处理的安全性

## 📦 发布流程

### 版本管理
- 遵循 [语义化版本](https://semver.org/)
- 主要版本：不兼容的 API 变更
- 次要版本：向后兼容的新功能
- 修补版本：向后兼容的 Bug 修复

### 发布检查清单
- [ ] 更新 CHANGELOG.md
- [ ] 更新版本号
- [ ] 更新文档
- [ ] 测试所有功能
- [ ] 检查安全性

## 🌟 贡献认可

我们重视每一位贡献者的努力：

- 所有贡献者将在 README 中得到认可
- 重要贡献者可能被邀请成为维护者
- 我们会为有价值的贡献提供反馈和指导

## 📞 获取帮助

如果您在贡献过程中遇到问题：

- 查看现有的 [Issues](https://github.com/your-username/codex-account-manager/issues)
- 在 [Discussions](https://github.com/your-username/codex-account-manager/discussions) 中提问
- 直接在 PR 中询问

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT 许可证](LICENSE) 下发布。