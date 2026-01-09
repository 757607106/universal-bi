# 前端体验优化实施方案

## 1. 响应式布局重构 (Responsive Layout)

### 目标
实现全设备适配（Mobile, Tablet, Desktop）。

### 实施细节
- **组件**: `frontend/src/layout/MainLayout.vue`
- **方案**:
  - 引入 `useWindowSize` 或 CSS Media Queries 监听屏幕宽度。
  - 新增 `Drawer` 组件用于移动端侧边栏。
  - 修改 `Sidebar` 组件支持 `collapsed` 状态。
  - **断点**:
    - `< 768px`: Sidebar 隐藏，Header 左侧显示 Hamburger 按钮。
    - `768px - 1024px`: Sidebar 自动收缩为图标模式 (64px 宽)。
    - `> 1024px`: Sidebar 展开 (240px 宽)。

## 2. 智能骨架屏系统 (Smart Skeleton System)

### 目标
减少用户等待焦虑，提供稳定的视觉预期。

### 实施细节
- **组件**: 新建 `frontend/src/components/Skeleton/DashboardSkeleton.vue`
- **设计**:
  - 模拟 Dashboard Card 结构：Title (20% width), Chart (Circle/Bar placeholder), Footer (Text line)。
  - 使用 SVG 或 CSS Gradients 实现 `shimmer` 扫光效果。
- **应用**:
  - 替换 `Dashboard/index.vue` 中的简易 `div` 骨架。

## 3. 交互与动效标准化 (Interaction & Motion)

### 目标
建立流畅、符合物理直觉的动效系统。

### 实施细节
- **全局配置**: `tailwind.config.js`
- **动效曲线**:
  - `ease-out-expo` (cubic-bezier(0.19, 1, 0.22, 1)) 用于进入动画。
  - `ease-in-expo` 用于退出动画。
  - 统一时长: `300ms` (交互), `500ms` (大面积转场)。
- **组件优化**:
  - 搜索框 (`el-input`): 增加 Focus 时的宽度延展动画 (`w-64` -> `w-80`)。
  - 按钮: 点击时增加 `scale-95` 反馈。

## 4. 视觉一致性 (Visual Consistency)

### 实施细节
- **网格系统**:
  - 检查所有 `margin/padding`，确保为 4 的倍数 (0.25rem)。
- **触控优化**:
  - 增加 `@media (pointer: coarse)` 查询，在触控设备上增大点击热区。

## 进度规划
1.  **Layout 重构**: 解决移动端不可用问题。
2.  **Skeleton 开发**: 提升 Dashboard 加载体验。
3.  **Motion 优化**: 润色交互细节。
