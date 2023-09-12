import os
import datetime
import smtplib
import time
import requests
import paramiko
import traceback
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import TimedRotatingFileHandler

# 配置参数
website_url = "https://api.tolosupplychains.com/SellingPartnerAPI/Login"  # 指定的网站 URL
email_sender = "junchengshen@hkaift.com"  # 发件人邮箱
email_recipients = [
    "junchengshen@hkaift.com",
    "changliu@hkaift.com",
    # "1835985714@qq.com"
]  # 收件人邮箱列表
smtp_server = "smtp.office365.com"  # SMTP 服务器
smtp_port = 587  # SMTP 服务器端口
smtp_username = "junchengshen@hkaift.com"  # SMTP 服务器用户名
smtp_password = "Junchs0!"  # SMTP 服务器密码
log_folder = "/home/yuxin/AmazonSellerAPI/yingshan/fordevelopment/check_website/logs"  # 日志文件夹
log_retention_days = 5  # 日志保留天数
process_name = "manage.py"  # 需要重启的进程名称
ssl_cert_file = "../ssl/fullchain.pem"  # SSL证书文件路径
ssl_key_file = "../ssl/privkey.pem"  # SSL私钥文件路径

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建按时间切割的文件处理器
log_file_path = os.path.join(log_folder, "website_check.log")

file_handler = TimedRotatingFileHandler(
    log_file_path, when="midnight", interval=1, backupCount=5)
file_handler.setLevel(logging.INFO)

# 配置日志格式
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(file_handler)


def send_email(subject, body):
    # 创建邮件内容
    msg = MIMEMultipart()
    msg["From"] = email_sender
    msg["To"] = ", ".join(email_recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # 连接 SMTP 服务器并发送邮件
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        recipients = email_recipients
        server.sendmail(email_sender, recipients, msg.as_string())


def send_restart_email():
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 检查日志文件是否已经存在，如果不存在则发送邮件
    subject = "【api.tolosupplychains.com网站已重新启动】" + now
    body = "网站已经重新启动，https://api.tolosupplychains.com/SellingPartnerAPI/Login "
    send_email(subject, body)
    logger.info("Website is restart and accessible.")


def send_success_email():
    global LAST_DAY
    global FAILED_TIMES
    FAILED_TIMES = 0
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 检查日志文件是否已经存在，如果不存在则发送邮件
    if LAST_DAY != now[:10]:
        logger.info(LAST_DAY)
        logger.info(now)
        LAST_DAY = now[:10]
        subject = "【api.tolosupplychains.com网站今日正常连接】" + now
        body = "网站正常连接 https://api.tolosupplychains.com/SellingPartnerAPI/Login "
        send_email(subject, body)
    logger.info("Website is accessible.")


def send_failed_email():
    global FAILED_TIMES
    FAILED_TIMES+=1
    if FAILED_TIMES <= 3:
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        subject = "【api.tolosupplychains.com网站失联告警】" + now + "，失去连接，请及时联系管理员"
        body = "网站失联，请及时联系管理员处理。 https://api.tolosupplychains.com/SellingPartnerAPI/Login"
        send_email(subject, body)
    logger.info("Website is unaccessible.")


def check_website():
    success = False
    try:

        try:
            response = requests.get(website_url, timeout=10)
            if response.status_code == 200:
                success = True
        except Exception as ex:
            logger.info(ex)

        if success:
            send_success_email()
            time.sleep(300)  # 等待 5 分钟
        else:
            send_failed_email()
            restart_process()
    except Exception as ex:
        logger.info(ex)
        traceback.print_exc()


def is_log_file_exists():
    today = datetime.date.today()
    log_file = os.path.join(log_folder, f"website_check_{today}.log")
    return os.path.isfile(log_file)




def restart_process():
    logger.info("restarting...")
    try:
        # SSH连接参数
        hostname = '192.168.5.148'
        port = 10023
        username = 'changliu'
        password = 'hkaift123!'
        sudo_password = 'hkaift123!'

        # 连接到服务器
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, port, username, password)

        # 打开交互式Shell连接
        shell = ssh_client.invoke_shell()
        time.sleep(1)

        # 切换到指定文件夹
        command_cd = 'cd /home/changliu/juncheng/AmazonDjangoUrl/DjangoServiceProject\n'

        shell.send(command_cd)
        logger.info(command_cd)
        time.sleep(1)

        # 杀死进程
        command_kill = "sudo kill -9 $(ps aux | grep manage.py | awk '{print $2}')\n"

        shell.send(command_kill)
        logger.info(command_kill)
        time.sleep(1)

        # 接收sudo提示并发送密码
        output = shell.recv(65535).decode('utf-8')
        if '[sudo] password for' in output:
            shell.send(sudo_password + '\n')
            time.sleep(1)

        # 重启应用
        command_restart = "nohup sudo python3 manage.py runserver_plus 0.0.0.0:443 --cert-file ../ssl/fullchain.pem --key-file ../ssl/privkey.pem > log.txt 2>&1 & disown\n"
        shell.send(command_restart)
        logger.info(command_restart)
        time.sleep(1)

        # 接收sudo提示并发送密码
        output = shell.recv(65535).decode('utf-8')
        if '[sudo] password for' in output:
            shell.send(sudo_password + '\n')
            time.sleep(1)

        # 关闭SSH连接
        shell.close()
        ssh_client.close()
        logger.info("restarted")
        send_restart_email()
    except Exception as ex:
        logger.info(ex)
        traceback.print_exc()


# 检查网站访问状态，每15分钟检查一次
LAST_DAY = datetime.date.today().strftime("%Y-%m-%d")
FAILED_TIMES = 0
logger.info(f"LAST_DAY:{LAST_DAY}")
while True:
    try:
        check_website()
    except Exception as ex:
        logger.info(ex)
        traceback.print_exc()
