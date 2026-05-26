# 自动化工具配置

## 工具组合建议

| 层次 | 推荐工具 | 作用 |
|------|---------|------|
| 交互式填写 | `commitizen` (cz) | 引导式填写，避免格式错误 |
| 提交时校验 | `commitlint` | 拒绝不合规范的提交信息 |
| Git Hook 管理 | `husky` | 在 git commit 时自动触发校验 |
| 生成 Changelog | `standard-version` | 根据提交记录自动生成版本日志 |
| VS Code 插件 | Conventional Commits | IDE 内可视化填写 |

## commitlint 配置

### 安装
```bash
npm install -D @commitlint/cli @commitlint/config-conventional
```

### commitlint.config.js
```js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // 允许中文 subject
    'subject-case': [0],
    // type 必须小写
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor',
      'perf', 'test', 'chore', 'ci', 'build', 'revert'
    ]],
    // subject 最长 100 字符
    'subject-max-length': [2, 'always', 100],
  }
};
```

## husky 配置

```bash
npm install -D husky
npx husky init
```

### .husky/commit-msg
```bash
#!/bin/sh
npx --no -- commitlint --edit "$1"
```

## commitizen 配置

### 安装
```bash
npm install -D commitizen cz-conventional-changelog
```

### package.json
```json
{
  "config": {
    "commitizen": {
      "path": "cz-conventional-changelog"
    }
  },
  "scripts": {
    "commit": "cz"
  }
}
```

使用 `npm run commit` 代替 `git commit`，会进入交互式选择：

```
? Select the type of change: (Use arrow keys)
❯ feat:     A new feature
  fix:      A bug fix
  docs:     Documentation only changes
  ...

? What is the scope of this change?
? Write a short description:
? Provide a longer description:
? Are there any breaking changes?
? Does this change affect any open issues?
```

## Python 项目替代方案

| 工具 | 替代 |
|------|------|
| husky + commitlint | `pre-commit` + `commitizen` (Python 版) |
| cz-conventional-changelog | `cz-conventional-gitmoji` 或 `cz-customizable` |

### Python commitizen 配置 (pyproject.toml)
```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"

[tool.commitizen.customize]
subject_max_length = 100
```

## VS Code 插件

搜索并安装 **Conventional Commits**（作者 vivaxy），编辑时按 `Ctrl+Shift+P` → `Conventional Commits`，在 IDE 内完成交互式填写，无需离开编辑器。
