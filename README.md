# emby-autoplay

随机 Emby 自动播放工具：
- 22~28 天随机一次
- 当天随机时刻
- 随机曲目
- 随机播放时长（>5 分钟，<20 分钟，偏向 10 分钟内）
- 使用 systemd 动态预约，不依赖 cron 轮询

## 功能特性

- 通过 Emby API 登录、获取媒体、建立播放会话、上报进度、停止播放
- 使用 `systemd-run` 动态注册下一次随机执行时间
- 执行完成后自动预约下一次
- 带状态文件和日志
- 可一键安装

## 目录结构

```text
emby-autoplay/
├── install.sh
├── uninstall.sh
├── README.md
└── src/
    ├── emby_keepalive.py
    ├── emby_keepalive_systemd_scheduler.py
    ├── emby_keepalive_systemd_runner.sh
    ├── run_emby_keepalive.sh
    └── emby_keepalive.env.example
```

## 依赖

- Linux + systemd
- Python 3
- `requests` Python 包

Debian/Ubuntu 一般可用：

```bash
apt-get update
apt-get install -y python3 python3-pip systemd
python3 -m pip install requests
```

## 一键安装

### 1. 克隆仓库

```bash
git clone https://github.com/Cd1s/emby-autoplay.git
cd emby-autoplay
```

### 2. 安装

```bash
chmod +x install.sh
./install.sh
```

安装脚本会：
- 复制文件到 `/opt/emby-autoplay`
- 生成配置文件 `/opt/emby-autoplay/emby_keepalive.env`
- 安装 systemd 动态预约脚本
- 立即注册下一次随机播放任务

## 配置

编辑：

```bash
nano /opt/emby-autoplay/emby_keepalive.env
```

示例：

```bash
EMBY_URL='http://your-emby-host:8096'
EMBY_USERNAME='your_username'
EMBY_PASSWORD='your_password'
EMBY_PLAY_SECONDS_DEFAULT='300'
EMBY_DEVICE_ID='emby-autoplay'
EMBY_CLIENT_NAME='EmbyAutoplay'
EMBY_CLIENT_VERSION='1.0.0'
EMBY_VERIFY_SSL='true'
EMBY_TIMEOUT='30'
```

## 手动测试

```bash
/opt/emby-autoplay/emby_keepalive_systemd_runner.sh
```

## 查看状态

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

## 卸载

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## 注意事项

- 需要 systemd 作为 init system
- 任务由 systemd timer 触发，不依赖 cron
- 如果修改了脚本，建议手动执行一次 runner 重新验证
