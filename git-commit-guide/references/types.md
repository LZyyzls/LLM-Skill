# Type 关键词定义与选用指南

## 标准类型词（Conventional Commits）

| type | 含义 | 使用场景 | 示例 |
|------|------|---------|------|
| **feat** | 新功能 | 新增用户可见的功能 | `feat(cart): 添加购物车批量删除` |
| **fix** | 缺陷修复 | 修复用户可感知的 bug | `fix(form): 修复手机号校验正则` |
| **docs** | 文档变更 | 仅改 README、注释、API 文档 | `docs: 更新部署说明` |
| **style** | 格式调整 | 空格、分号、换行，不影响逻辑 | `style: 统一缩进为 4 空格` |
| **refactor** | 重构 | 改代码结构但不改外部行为 | `refactor(db): 提取连接池配置` |
| **perf** | 性能优化 | 提升速度、减少内存的改动 | `perf(query): 为 user_id 添加索引` |
| **test** | 测试相关 | 添加或修改测试代码 | `test(auth): 补充登录失败用例` |
| **chore** | 杂项维护 | 依赖更新、构建脚本、配置 | `chore: 升级 lodash 到 4.17.21` |
| **ci** | CI/CD | 持续集成/部署配置 | `ci: 添加 PR 自动检查流水线` |
| **build** | 构建系统 | 影响编译、打包的改动 | `build: 切换打包工具到 Vite` |
| **revert** | 回滚 | 撤销之前的提交 | `revert: 回退 feat(auth): 添加 JWT` |

## 选型决策树

```
这个改动用影响外部行为吗？
  ├─ 是 → 新增功能？ → feat
  │      └─ 修复 bug？ → fix
  │
  └─ 否 → 只改代码不改行为？ → refactor
          ├─ 只改注释/文档？ → docs
          ├─ 只改格式？ → style
          ├─ 只改测试？ → test
          ├─ 性能相关？ → perf
          ├─ CI/构建相关？ → ci / build
          └─ 以上都不是？ → chore
```

## 常见选错案例

| 实际改动 | 错误 type | 正确 type | 原因 |
|---------|-----------|-----------|------|
| 修改 ESLint 规则 | `refactor` | `style` | 只影响格式，不影响逻辑 |
| 更新 README 中的安装步骤 | `chore` | `docs` | 纯文档变更 |
| 换一个更快的排序算法 | `refactor` | `perf` | 目的明确是性能 |
| 加一个日志打印 | `feat` | `chore` | 非用户可见功能 |
| 把两个函数合并为一个 | `fix` | `refactor` | 没修 bug，是结构调整 |

## scope（范围）建议

| 粒度 | 示例 | 适用项目 |
|------|------|---------|
| 模块级 | `auth`, `payment`, `search` | 中大型项目 |
| 组件级 | `Button`, `Modal`, `Table` | 组件库 |
| 服务级 | `user-service`, `gateway` | 微服务 |
| 不加 scope | `feat: 初始化项目` | 小型/个人项目 |
