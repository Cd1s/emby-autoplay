# emby-autoplay

随机 Emby 自动播放工具：
- 22~28 天随机一次
- 当天随机时刻
- 随机曲目
- 随机播放时长（>5 分钟，<20 分钟，偏向 10 分钟内）
- 使用 systemd 动态预约，不依赖 cron 轮询
- 支持交互式安装
- 安装后提供 `embyautoplay` 管理命令
- 支持卸载、修改配置、查看下次运行、查看日志、手动测试

## 功能特性

- 通过 Emby API 登录、获取媒体、建立播放会话、上报进度、停止播放
- 使用 `systemd-run` 动态注册下一次随机执行时间
- 执行完成后自动预约下一次
- 带状态文件和日志
- 支持一键安装（无需 git clone）
- 支持交互配置：协议、域名、端口、用户名、密码、随机周期、播放时长范围
- 安装后可直接使用 `embyautoplay` 进入管理菜单

## 一键安装（无需克隆仓库）

当前推荐使用**固定 commit 安装器**，避免 `main` 分支的 Raw CDN 缓存导致拿到旧脚本。

### 推荐方式：下载后执行

#### curl

```bash
curl -fsSL https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh -o install-online.sh && bash install-online.sh
```

#### wget

```bash
wget -qO install-online.sh https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh && bash install-online.sh
```

### 也可以直接 pipe 给 bash

#### curl

```bash
curl -fsSL https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh | bash
```

#### wget

```bash
wget -qO- https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh | bash
```

### 重要说明

下面这种命令**只会把脚本打印到屏幕，不会执行**：

```bash
curl -fsSL https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh
wget -qO- https://raw.githubusercontent.com/Cd1s/emby-autoplay/9b0cc91/install-online.sh
```

安装过程会交互询问：
- http 还是 https
- 域名 / IP
- 端口
- 用户名
- 密码
- 随机运行间隔（最小天数 / 最大天数）
- 随机播放时长范围
- 偏好 10 分钟内的概率
- 是否校验 SSL
- 请求超时

安装完成后会自动：
- 安装到 `/opt/emby-autoplay`
- 生成配置文件 `/opt/emby-autoplay/emby_keepalive.env`
- 生成状态文件 `/opt/emby-autoplay/emby_keepalive_state.json`
- 注册下一次 systemd 动态任务
- 创建管理命令：`embyautoplay`

## 管理命令

安装完成后直接输入：

```bash
embyautoplay
```

菜单功能包括：
- 查看状态
- 查看下次运行
- 查看播放日志
- 查看调度日志
- 手动测试运行
- 修改配置
- 重新预约下一次运行
- 卸载

## 主要路径

```text
/opt/emby-autoplay/
├── emby_keepalive.py
├── emby_keepalive_config.py
├── emby_keepalive_systemd_scheduler.py
├── emby_keepalive_systemd_runner.sh
├── run_emby_keepalive.sh
├── interactive_install.py
├── embyautoplay
├── emby_keepalive.env
├── emby_keepalive_state.json
└── logs/
    ├── emby_keepalive.log
    └── emby_keepalive_scheduler.log
```

## 查看信息

### 查看当前计划

```bash
cat /opt/emby-autoplay/emby_keepalive_state.json
```

### 查看 timer

```bash
systemctl list-timers --all | grep emby-keepalive
```

### 查看播放日志

```bash
tail -n 50 /opt/emby-autoplay/logs/emby_keepalive.log
```

### 查看调度日志

```bash
tail -n 50 /opt/emby-autoplay/logs/emby_keepalive_scheduler.log
```

## 手动测试

```bash
/opt/emby-autoplay/emby_keepalive_systemd_runner.sh
```

或者：

```bash
embyautoplay
```

然后选“手动测试运行”。

## 卸载

### 方式 1：管理菜单中卸载

```bash
embyautoplay
```

然后选“卸载”。

### 方式 2：直接执行卸载脚本

```bash
/opt/emby-autoplay/uninstall.sh
```

## 依赖

- Linux + systemd
- Python 3
- `requests` Python 包
- `curl` 或 `wget`（在线安装时）

Debian/Ubuntu：

```bash
apt-get update
apt-get install -y python3 python3-pip systemd curl
python3 -m pip install requests
```
