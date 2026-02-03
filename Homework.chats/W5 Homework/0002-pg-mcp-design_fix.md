# Design Fix: PG-MCP Server 增强设计文档

**文档编号**: 0002-pg-mcp-design_fix  
**状态**: 提案 (Proposed)  
**日期**: 2026-02-03  
**作者**: Antigravity  

## 1. 背景与问题描述

根据对现有 PG-MCP 服务器的测试与审计（参考 TEST_QUERIES.md 及 TEST_RESULTS.md），发现当前实现存在以下关键缺陷，阻碍了系统的生产可用性：

1. **多数据库与安全控制失效**：
    * 设计上承诺支持多数据库，但实际仅实现了单一执行器（Executor），导致无法正确处理针对不同数据库的请求。
    * 缺乏强制的表/列级访问控制，无法拦截对敏感数据的非授权访问。
    * 缺少对 `EXPLAIN` 语句的安全策略，可能暴露数据库内部统计信息。

2. **弹性与可观测性缺失**：
    * 速率限制（Rate Limiting）、重试/退避（Retry/Backoff）机制仅停留在设计概念，代码中未实际调用。
    * 缺乏指标（Metrics）与追踪（Tracing）系统，导致难以监控系统健康状态及排查故障。

3. **代码质量与测试不足**：
    * 响应模型中存在重复代码（如冗余的 `to_dict` 方法）。
    * 配置对象中存在未使用的字段，造成维护困惑。
    * 测试覆盖率低，导致系统行为与设计意图偏离，且难以验证修复后的正确性。

本设计文档旨在提出一套具体的修复与改进方案，以解决上述问题。

---

## 2. 详细设计方案

### 2.1 多数据库与连接管理重构

**目标**: 启用真正的多数据库支持，确保请求被路由到正确的数据库实例，并实现连接隔离。

**方案**:

1. **引入 `ConnectionManager`**:
    * 替代当前的全局单一 `executor`。
    * 维护一个 `Dict[str, PgExecutor]` 映射，Key 为数据库连接标识（如 DSN 哈希或别名），Value 为独立的执行器实例。
    * 实现连接池管理，支持按需延迟初始化连接（Lazy Loading）和空闲回收。

2. **请求路由机制**:
    * 在 MCP 工具调用（如 `query` 工具）的参数中明确 `database` 字段。
    * 中间件层解析请求参数，通过 `ConnectionManager` 获取对应的 Executor。如果未指定，使用默认数据库，但需记录警告。

### 2.2 安全控制增强 (Security Layer)

**目标**: 在 SQL 执行前实施细粒度的权限校验。

**方案**:

1. **查询拦截器 (Query Interceptor/Validator)**:
    * 在 Executor 执行 SQL 前引入解析步骤（可利用 `sqlglot` 或简单正则/AST）。
    * **表级权限**: 检查 SQL 中涉及的表是否在允许列表中 (Allowlist)。
    * **列级权限**: (高级) 检查涉及的列是否被禁止访问。

2. **EXPLAIN 策略**:
    * 配置项 `allow_explain: boolean`。
    * 如果为 `False`，拦截所有以 `EXPLAIN` 开头的查询。
    * 如果为 `True`，仅允许在只读事务中执行，且可能限制输出格式。

3. **只读强制**:
    * 确保所有非特权连接都默认设置 `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`。

### 2.3 弹性与可观测性集成

**目标**: 提高系统的稳定性和可调试性。

**方案**:

1. **中间件模式 (Middleware Pattern)**:
    * 采用装饰器或中间件模式包裹核心处理函数。

2. **速率限制 (Rate Limiting)**:
    * 实现基于 Token Bucket 的限流器。
    * 粒度：全局限流 + 基于 Client/User 的限流（如果 MCP 协议传递了身份信息）。
    * 在达到阈值时抛出特定的 MCP 错误代码。

3. **重试机制 (Retry Policy)**:
    * 针对瞬态错误（Transient Errors，如连接超时、死锁）实现指数退避重试 (Exponential Backoff)。
    * 配置：`max_retries`, `base_delay`, `max_delay`.

4. **结构化日志与指标**:
    * 引入结构化日志（JSON Log），记录 `request_id`, `database`, `query_hash`, `duration_ms`, `status`.
    * 暴露基础指标（如 Prometheus 格式或简单的内存中计数器），供 `/metrics` 端点（如果支持）或日志定期输出。

### 2.4 模型与代码清理

**目标**: 消除技术债，规范代码风格。

**方案**:

1. **Pydantic 模型优化**:
    * 移除手写的 `to_dict` 方法，直接使用 Pydantic 内置的 `model_dump()`。
    * 审查 `Config` 类，移除所有未被引用的字段，或者明确标记为 `Pending Deprecation`。

2. **统一错误处理**:
    * 建立统一的异常体系 `McpServerException`，所有内部错误均捕获并转换为标准的 MCP 协议错误响应，防止堆栈信息泄露。

---

## 3. 实施计划 (Roadmap)

### 阶段 1: 核心重构与清理 (Foundation)

* **任务 1.1**: 清理 Pydantic 模型，移除冗余方法和无效配置。
* **任务 1.2**: 建立 `ConnectionManager` 基础结构，支持配置加载。

### 阶段 2: 安全增强 (Security)

* **任务 2.1**: 实现 SQL 验证器，支持表白名单配置。
* **任务 2.2**: 集成到 `execute_query` 流程中，验证拦截逻辑。

### 阶段 3: 弹性与监控 (Reliability)

* **任务 3.1**: 添加 `RateLimit` 和 `Retry` 装饰器。
* **任务 3.2**: 完善日志系统，确保关键路径的可观测性。

### 阶段 4: 测试补全 (Verification)

* **任务 4.1**: 为上述新模块编写单元测试。
* **任务 4.2**: 使用 fixtures 中的多数据库场景进行集成测试，验证路由与权限控制。

## 4. 验证标准

1. **多库隔离**: 请求 A 库的查询不应访问到 B 库的数据（除非明确跨库）。
2. **权限拦截**: 访问未授权表应返回 `PermissionDenied`，而不是数据库原生错误。
3. **稳定性**: 在模拟高并发或网络抖动下，系统应能通过重试恢复或优雅降级（限流），不崩溃。
4. **代码覆盖**: 新增核心模块的测试覆盖率应达到 90% 以上。
