# 语言选择策略：中文 vs 英文

## 推荐方案

| 场景 | 推荐语言 | 理由 |
|------|:--------:|------|
| 开源项目 | **英文** | 国际协作、issue 关联、changelog 自动生成 |
| 企业内部项目 | **中文** | 团队沟通效率、技术细节表达更准确 |
| 混合团队（中外协作） | **英文** | 统一标准，降低理解门槛 |
| 个人项目 | 随你 | 但建议养成英文习惯 |

## 英文提交规范

### 动词使用
- subject 用祈使句原形：`add` 而非 `added`、`adds`
- 首字母小写，不加句号

```
✅ feat: add rate limiting to login API
❌ feat: Added rate limiting to login API.
```

### 常用动词对照

| 中文 | 英文 | 中文 | 英文 |
|------|------|------|------|
| 添加 | add | 移除 | remove |
| 修复 | fix | 更新 | update |
| 重构 | refactor | 优化 | optimize |
| 实现 | implement | 支持 | support |
| 合并 | merge | 回退 | revert |

## 中文提交规范

### 基本规则
- 使用简洁直白的动词开头
- 不超过 25 个汉字
- 不加句号

```
✅ feat(auth): 添加密码强度校验
✅ fix(api): 修复并发请求时的 session 冲突
❌ feat: 做了一个关于用户认证模块的密码强度的校验功能（太长）
```

### 常见问题

**Q: 中英混合可以吗？**
A: 可以，但有限制。type 和 scope 保持英文，subject 用中文。

```
✅ fix(WebSocket): 修复断线重连后消息重复推送
✅ docs(api): 补充 rate limiting 的错误码说明
❌ 修复(认证): 用户登录时session丢失的问题  ← type 不要翻译
```

**Q: 中英混合时关键词怎么处理？**
A: 技术专有名词保留英文，不要硬翻。

```
✅ feat(task): 为 Celery 任务添加超时重试机制
❌ feat(task): 为芹菜任务添加超时重试机制  ← Celery 不应翻译
```

## 团队统一建议

最差的情况不是"用了中文"，而是**有人用中文有人用英文**。建议：

1. 在项目 README 或 CONTRIBUTING.md 中明确约定语言
2. 用 commitlint 的 `subject-case` 规则来适配中文（关闭英文大小写检查）
3. 核心原则：**可读性 > 形式**。团队能看懂、能检索最重要
