# emby-autoplay

Emby 自动播放工具。

功能：
- 22~28 天随机一次
- 当天随机时刻
- 随机曲目
- 随机播放时长（大于 5 分钟，小于 20 分钟，偏向 10 分钟以内）
- 使用 systemd 动态预约
- 安装后提供 `embyautoplay` 管理命令

---

## 一键安装

### curl

```bash
curl -fsSL https://raw.githubusercontent.com/Cd1s/emby-autoplay/refs/heads/main/install-online.sh -o install-online.sh && bash install-online.sh
```

### wget

```bash
wget -qO install-online.sh https://raw.githubusercontent.com/Cd1s/emby-autoplay/refs/heads/main/install-online.sh && bash install-online.sh
```

---

## 安装过程

安装时会交互询问：
- http / https
- 域名或 IP
- 端口
- 用户名
- 密码
- 最小运行天数
- 最大运行天数
- 最短播放秒数
- 偏好最长秒数
- 硬上限最长秒数
- 是否校验 SSL
- 请求超时

---

## 安装后使用

进入管理菜单：

```bash
embyautoplay
```

菜单功能：
- 查看状态
- 查看下次运行
- 查看播放日志
- 查看调度日志
- 手动测试运行
- 修改配置
- 重新预约下一次运行
- 卸载

---

## 常用路径

```text
/opt/emby-autoplay/
```

日志：

```text
/opt/emby-autoplay/logs/emby_keepalive.log
/opt/emby-autoplay/logs/emby_keepalive_scheduler.log
```

状态文件：

```text
/opt/emby-autoplay/emby_keepalive_state.json
```

---

## 手动测试

```bash
embyautoplay
```

选择：

```text
5. 手动测试运行
```

---

## 卸载

### 菜单卸载

```bash
embyautoplay
```

选择：

```text
8. 卸载
```

### 直接卸载脚本

```bash
/opt/emby-autoplay/uninstall.sh
```

---

## 更新

重新执行安装命令即可覆盖更新：

```bash
curl -fsSL https://raw.githubusercontent.com/Cd1s/emby-autoplay/refs/heads/main/install-online.sh -o install-online.sh && bash install-online.sh
```
