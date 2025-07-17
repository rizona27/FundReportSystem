import sys
import os
import configparser
import re
import json
import requests
import time
import csv
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import urllib3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit, 
                             QCheckBox, QDialog, QFormLayout, QMessageBox, QDialogButtonBox,
                             QDoubleSpinBox, QSpinBox, QFileDialog, QDesktopWidget, QStatusBar,
                             QSizePolicy, QScrollArea, QGridLayout, QTextBrowser)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QDoubleValidator, QTextCursor
from urllib.parse import quote  # 添加URL编码支持

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 默认配置（增加企业微信推送选项）
DEFAULT_CONFIG = {
    'mobile': {'enabled': '0', 'bark_enabled': '0', 'gotify_enabled': '0', 'wecom_enabled': '0'},
    'pc': {'enabled': '0', 'by_fund': '1', 'by_user': '1'},
    'advanced': {
        'bark_url': '',
        'bark_token': '',
        'gotify_url': '',
        'gotify_token': '',
        'wecom_corpid': '',
        'wecom_agentid': '',
        'wecom_secret': '',
        'wecom_proxy_url': '',
        'benchmark_funds': '000001,110022',
        'max_message_bytes': '2048',
        'max_retries': '3',
        'retry_delay': '5',
        'target_return': '5.0'
    }
}

# 添加资源访问路径 - 确保打包后能正确访问资源
if getattr(sys, 'frozen', False):
    # 打包后的执行路径
    base_dir = os.path.dirname(sys.executable)
else:
    # 开发环境路径
    base_dir = os.path.dirname(os.path.abspath(__file__))

def get_app_base_dir():
    """获取应用程序所在的目录（.app文件所在的目录）"""
    # 在打包的应用程序中，sys.executable指向.exe文件
    # 在开发环境中，sys.executable指向Python解释器
    
    # 使用全局base_dir变量
    return base_dir

# 主窗口类
class FundReportSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("基金报告推送系统")
        self.setFixedSize(800, 550)  # 增加高度到550，提供更多底部空间
        
        # 设置应用基础目录
        self.base_dir = get_app_base_dir()
        self.config_dir = os.path.join(self.base_dir, "config")
        self.config_file = os.path.join(self.config_dir, "config.ini")
        self.funds_file = os.path.join(self.config_dir, "funds.txt")
        self.report_dir = os.path.join(self.base_dir, "report")
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 设置新的配色方案
        self.set_refreshed_style()
        
        self.setup_ui()
        self.load_config()
        self.check_funds_file()
        
        # 居中显示窗口
        self.center_window()
    
    def center_window(self):
        """居中显示窗口"""
        frame = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())
    
    def set_refreshed_style(self):
        """设置新的配色方案 - 更明亮、更鲜明"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(245, 248, 250))       # 更亮的背景色
        palette.setColor(QPalette.WindowText, QColor(44, 62, 80))       # 文字色 #2C3E50
        palette.setColor(QPalette.Base, QColor(255, 255, 255))          # 输入框背景色
        palette.setColor(QPalette.AlternateBase, QColor(230, 240, 250)) # 交替背景 - 更亮的蓝色调
        palette.setColor(QPalette.Button, QColor(91, 155, 213))         # 按钮背景 - 明亮的蓝色 #5B9BD5
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))    # 按钮文字
        palette.setColor(QPalette.Highlight, QColor(70, 130, 180))      # 高亮色 - 更深的蓝色 #4682B4
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        self.setPalette(palette)
        
        # 设置全局样式 - 更紧凑、更鲜明
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F8FA;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #A0C0E0;
                border-radius: 8px;
                margin-top: 0.5ex;
                padding: 8px;
                background-color: #E6F0F8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #2C3E50;
            }
            QPushButton {
                background-color: #5B9BD5;
                color: white;
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: bold;
                min-height: 25px;
                border: 1px solid #3A7CBA;
            }
            QPushButton:hover {
                background-color: #4A8BC5;
            }
            QPushButton:pressed {
                background-color: #3A7CBA;
            }
            QPushButton:disabled {
                background-color: #A0C0E0;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #B0C0D0;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
                font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
            }
            QCheckBox {
                spacing: 5px;
                color: #2C3E50;
            }
            QTextEdit {
                font-size: 11px;
            }
            QLabel {
                color: #2C3E50;
            }
            QDoubleSpinBox, QSpinBox {
                padding: 3px;
                border-radius: 4px;
                border: 1px solid #B0C0D0;
            }
            /* 状态栏样式 - 增加上下边距 */
            QStatusBar {
                background-color: #E0E8F0;
                border-top: 1px solid #C0D0E0;
                padding: 6px 15px;  /* 减少上下内边距 */
                height: 35px;        /* 增加状态栏高度 */
            }
            QStatusBar QLabel {
                margin-left: 5px;
            }
            QStatusBar::item {
                border: none;
                padding: 0 5px;
            }
            /* 状态栏按钮样式 - 增加边距 */
            QStatusBar QPushButton {
                margin: 2px 8px;    /* 减少按钮边距 */
                min-height: 28px;   /* 增加按钮高度 */
                min-width: 80px;    /* 增加按钮最小宽度 */
            }
            /* 帮助对话框样式 */
            QDialog#HelpDialog {
                background-color: #F5F8FA;
            }
            QTextBrowser {
                background-color: white;
                border: 1px solid #B0C0D0;
                border-radius: 4px;
                padding: 10px;
                font-size: 11px;
                font-family: Arial, sans-serif;
            }
            
            /* 特殊按钮样式 */
            QPushButton#runButton {
                background-color: #4CAF50;  /* 绿色 */
                font-size: 13px;
                min-height: 40px;
                padding: 8px;
            }
            QPushButton#runButton:hover {
                background-color: #45a049;
            }
            QPushButton#runButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#configButton {
                background-color: #5B9BD5;  /* 蓝色 */
            }
            QPushButton#helpButton {
                background-color: #FF9800;  /* 橙色 */
            }
        """)
    
    def setup_ui(self):
        # 主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧配置区
        config_group = QGroupBox("配置功能区")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(8)
        
        # ========== 手机端推送设置 ==========
        mobile_group = QGroupBox("推送到手机端")
        mobile_layout = QVBoxLayout(mobile_group)
        mobile_layout.setSpacing(8)
        
        # 手机端推送总开关
        self.mobile_cb = QCheckBox("启用手机端推送")
        mobile_layout.addWidget(self.mobile_cb)
        
        # 推送方式选择
        push_layout = QVBoxLayout()
        push_layout.setContentsMargins(15, 3, 3, 3)
        
        # Bark设置
        self.bark_cb = QCheckBox("启用 Bark 推送[IOS]")
        push_layout.addWidget(self.bark_cb)
        
        # Gotify设置
        self.gotify_cb = QCheckBox("启用 Gotify 推送[Android]")
        push_layout.addWidget(self.gotify_cb)
        
        # 企业微信推送设置
        self.wecom_cb = QCheckBox("启用企业微信推送")
        push_layout.addWidget(self.wecom_cb)
        
        mobile_layout.addLayout(push_layout)
        
        config_layout.addWidget(mobile_group)
        
        # ========== PC端推送设置 ==========
        pc_group = QGroupBox("推送到电脑端")
        pc_layout = QVBoxLayout(pc_group)
        pc_layout.setSpacing(8)
        
        # PC端推送总开关
        self.pc_cb = QCheckBox("启用电脑端推送")
        pc_layout.addWidget(self.pc_cb)
        
        # 报告类型设置
        type_layout = QVBoxLayout()
        type_layout.setContentsMargins(15, 3, 3, 3)
        self.by_fund_cb = QCheckBox("按基金分类生成报告")
        self.by_fund_cb.setChecked(True)
        type_layout.addWidget(self.by_fund_cb)
        self.by_user_cb = QCheckBox("按客户分类生成报告")
        self.by_user_cb.setChecked(True)
        type_layout.addWidget(self.by_user_cb)
        pc_layout.addLayout(type_layout)
        
        config_layout.addWidget(pc_group)
        
        # ========== 按钮区 ==========
        # 高级设置按钮
        self.adv_btn = QPushButton("高级设置")
        self.adv_btn.setObjectName("configButton")  # 设置对象名用于样式
        self.adv_btn.setFixedHeight(35)
        config_layout.addWidget(self.adv_btn)
        
        # 使用说明按钮
        help_btn = QPushButton("使用说明")
        help_btn.setObjectName("helpButton")  # 设置对象名用于样式
        help_btn.setFixedHeight(35)
        config_layout.addWidget(help_btn)
        
        # 主要操作按钮 - 单独一行
        config_layout.addSpacing(10)  # 添加间距
        
        self.run_btn = QPushButton("生成并推送报告")
        self.run_btn.setObjectName("runButton")  # 设置对象名用于样式
        self.run_btn.setFixedHeight(45)
        config_layout.addWidget(self.run_btn)
        
        # 添加弹性空间使按钮位于顶部
        config_layout.addStretch(1)
        
        # 右侧日志区
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 5, 5, 5)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Menlo", 10))  # 设置等宽字体
        log_layout.addWidget(self.log_area)
        
        # 添加到主布局
        main_layout.addWidget(config_group, 1)
        main_layout.addWidget(log_group, 2)
        
        # 底部状态栏 - 简化处理
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        
        # 设置主窗口
        self.setCentralWidget(main_widget)
        
        # 连接信号
        self.mobile_cb.toggled.connect(self.toggle_mobile)
        self.pc_cb.toggled.connect(self.toggle_pc)
        self.adv_btn.clicked.connect(self.show_advanced)
        self.run_btn.clicked.connect(self.run_report)
        help_btn.clicked.connect(self.show_help)
        
        # 初始状态
        self.toggle_mobile(False)
        self.toggle_pc(False)
    
    def toggle_mobile(self, checked):
        """切换手机端推送设置状态"""
        self.bark_cb.setEnabled(checked)
        self.gotify_cb.setEnabled(checked)
        self.wecom_cb.setEnabled(checked)
    
    def toggle_pc(self, checked):
        """切换PC端推送设置状态"""
        self.by_fund_cb.setEnabled(checked)
        self.by_user_cb.setEnabled(checked)
    
    def show_advanced(self):
        dialog = AdvancedConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.save_config()
    
    def show_help(self):
        """显示美观的帮助文档"""
        help_dialog = QDialog(self)
        help_dialog.setObjectName("HelpDialog")  # 设置对象名用于样式表
        help_dialog.setWindowTitle("使用指南")
        help_dialog.setFixedSize(700, 500)
        
        layout = QVBoxLayout(help_dialog)
        
        # 创建文本浏览器显示帮助内容
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        
        # 设置HTML格式的帮助内容
        html_content = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }
                h1 {
                    color: #2C3E50;
                    font-size: 18px;
                    border-bottom: 2px solid #5B9BD5;
                    padding-bottom: 5px;
                }
                h2 {
                    color: #2C3E50;
                    font-size: 16px;
                    margin-top: 20px;
                }
                .section {
                    background-color: #F0F7FF;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    border-left: 3px solid #5B9BD5;
                }
                .section-title {
                    font-weight: bold;
                    color: #2C3E50;
                    margin-bottom: 5px;
                }
                .note {
                    background-color: #FFF8E1;
                    border-left: 3px solid #FFC107;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                }
                .code {
                    font-family: Consolas, Monaco, monospace;
                    background-color: #F5F5F5;
                    padding: 2px 4px;
                    border-radius: 3px;
                }
                .highlight {
                    background-color: #E1F5FE;
                    padding: 2px 4px;
                    border-radius: 3px;
                }
                .contact {
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <h1>基金报告推送系统</h1>
            
            <div class="section">
                <div class="section-title">1. 系统介绍</div>
                <p>本系统能够自动获取基金净值数据，生成持仓报告，并支持IOS/Android手机端通知软件、企业微信及PC等多种方式推送报告给用户。</p>
                
                <p><strong>主要功能：</strong></p>
                <ul>
                    <li>自动获取基金最新净值数据</li>
                    <li>计算持仓收益和年化收益率</li>
                    <li>生成详细的持仓报告</li>
                    <li>通过Gotify、Bark或企业微信等平台推送报告到手机</li>
                    <li>生成报告文件保存到电脑</li>
                </ul>
            </div>
            
            <div class="section">
                <div class="section-title">2. 配置说明</div>
                
                <p><strong>[推送到手机端]</strong></p>
                <ul>
                    <li>启用手机端推送：勾选后可使用Bark、Gotify或企业微信推送</li>
                    <li>Bark推送：需要在高级设置中配置Bark服务器地址和设备密钥</li>
                    <li>Gotify推送：需要在高级设置中配置Gotify服务器地址和应用Token</li>
                    <li>企业微信推送：需要在高级设置中配置企业微信相关参数</li>
                </ul>
                
                <p><strong>[推送到电脑端]</strong></p>
                <ul>
                    <li>启用电脑端推送：勾选后可在电脑上生成报告文件</li>
                    <li>按基金分类生成：生成以基金代码命名的报告文件</li>
                    <li>按客户分类生成：生成以客户名称命名的报告文件</li>
                    <li>目标收益报告：生成所有超过目标年化收益率的基金持仓报告</li>
                </ul>
                
                <p>报告文件保存在程序同一目录下的<span class="highlight">report</span>文件夹中：</p>
                <ul>
                    <li><span class="code">report/by_fund/基金代码_基金名称/年月日时分.txt</span></li>
                    <li><span class="code">report/by_user/用户名/年月日时分.txt</span></li>
                    <li><span class="code">report/已达目标收益.txt</span></li>
                </ul>
            </div>
            
            <div class="section">
                <div class="section-title">3. 快速开始</div>
                
                <ol>
                    <li>打开软件后默认会在程序同一目录下创建 <span class="code">config/funds.txt</span> 文件</li>
                    <li>按照指定格式添加基金持仓数据：
                        <div class="note">
                            <p><strong>格式：</strong> 用户名,基金代码,买入日期,买入金额(元),持仓份额</p>
                            <p><strong>示例：</strong></p>
                            <p class="code">张三,163406,2023-01-01,100000.00,50000.00</p>
                            <p class="code">张三,110022,2023-05-15,50000.00,30000.00</p>
                            <p class="code">李四,001718,2024-01-01,80000.00,40000.00</p>
                        </div>
                    </li>
                    <li>配置推送方式</li>
                    <li>点击"生成并推送报告"按钮</li>
                </ol>
            </div>
            
            <div class="section">
                <div class="section-title">4. 常见问题Q&A</div>
                
                <p><strong>Q: 为什么没有收到推送？</strong></p>
                <p>A: 请检查推送配置是否正确，网络是否通畅，以及推送服务器是否正常运行。</p>
                
                <p><strong>Q: 基金数据获取失败怎么办？</strong></p>
                <p>A: 请检查基金代码是否正确，网络连接是否正常，或者联系作者更新版本/API接口再试。</p>
                
                <p><strong>Q: 如何查看历史报告？</strong></p>
                <p>A: 报告保存在程序所在目录的<span class="highlight">"report"</span>文件夹中。</p>
                
                <p><strong>Q: 目标收益报告是什么？</strong></p>
                <p>A: 目标收益报告汇总了所有年化收益率超过设定目标的基金持仓情况，便于快速识别。</p>
            </div>
            
            <div class="contact">
                <p>By : rizona.cn@gmail.com</p>
                <p>版本: 3.3 | 更新日期: 2025年6月</p>
            </div>
        </body>
        </html>
        """
        
        text_browser.setHtml(html_content)
        layout.addWidget(text_browser)
        
        # 关闭按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(help_dialog.reject)
        layout.addWidget(btn_box)
        
        help_dialog.exec_()
    
    def log_message(self, message, level="info"):
        """添加日志消息"""
        if level == "error":
            color = "#e74c3c"  # 红色
            prefix = "[错误] "
        elif level == "warning":
            color = "#f39c12"  # 黄色
            prefix = "[警告] "
        elif level == "success":
            color = "#27ae60"  # 绿色
            prefix = "[成功] "
        else:
            color = "#2980b9"  # 蓝色
            prefix = "[信息] "
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        html_message = f'<span style="color:{color}">[{timestamp}] {prefix}{message}</span>'
        
        self.log_area.append(html_message)
        
        # 自动滚动到底部
        self.log_area.moveCursor(QTextCursor.End)
        
        # 更新状态栏
        self.status_bar.showMessage(f"最新状态: {message}", 5000)
    
    def load_config(self):
        """从配置文件加载设置"""
        self.config = configparser.ConfigParser()
        
        # 如果配置文件存在，则加载
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            
            # 加载基本配置
            # 手机端设置
            self.mobile_cb.setChecked(self.config.getboolean('mobile', 'enabled', fallback=False))
            self.bark_cb.setChecked(self.config.getboolean('mobile', 'bark_enabled', fallback=False))
            self.gotify_cb.setChecked(self.config.getboolean('mobile', 'gotify_enabled', fallback=False))
            self.wecom_cb.setChecked(self.config.getboolean('mobile', 'wecom_enabled', fallback=False))
            
            # PC端设置
            self.pc_cb.setChecked(self.config.getboolean('pc', 'enabled', fallback=False))
            self.by_fund_cb.setChecked(self.config.getboolean('pc', 'by_fund', fallback=True))
            self.by_user_cb.setChecked(self.config.getboolean('pc', 'by_user', fallback=True))
            
            self.log_message("配置加载完成")
        else:
            # 如果配置文件不存在，使用默认配置（不创建文件）
            self.config.read_dict(DEFAULT_CONFIG)
            self.log_message("使用默认配置")
        
        # 更新控件状态
        self.toggle_mobile(self.mobile_cb.isChecked())
        self.toggle_pc(self.pc_cb.isChecked())
    
    def save_config(self):
        """保存配置到文件（仅在用户操作时保存）"""
        # 手机端配置
        self.config['mobile'] = {
            'enabled': '1' if self.mobile_cb.isChecked() else '0',
            'bark_enabled': '1' if self.bark_cb.isChecked() else '0',
            'gotify_enabled': '1' if self.gotify_cb.isChecked() else '0',
            'wecom_enabled': '1' if self.wecom_cb.isChecked() else '0'
        }
        
        # PC端配置
        self.config['pc'] = {
            'enabled': '1' if self.pc_cb.isChecked() else '0',
            'by_fund': '1' if self.by_fund_cb.isChecked() else '0',
            'by_user': '1' if self.by_user_cb.isChecked() else '0'
        }
        
        # 高级配置已在高级设置对话框中保存
        
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        
        self.log_message("配置已保存")
    
    def check_funds_file(self):
        """检查基金数据文件"""
        if not os.path.exists(self.funds_file):
            self.log_message("未找到funds.txt文件，正在创建示例文件...", "warning")
            
            try:
                with open(self.funds_file, 'w', encoding='utf-8') as f:
                    f.write("# 用户名,基金代码,买入日期,买入金额(元),持仓份额\n")
                    f.write("# 示例数据（请删除注释行）：\n")
                    f.write("张三,163406,2023-01-01,100000.00,50000.00\n")
                    f.write("张三,110022,2023-05-15,50000.00,30000.00\n")
                    f.write("李四,001718,2024-01-01,80000.00,40000.00\n")
                
                self.log_message(f"已创建示例funds.txt文件，位置: {self.funds_file}", "warning")
                self.log_message("请编辑该文件后重新运行程序", "warning")
            except Exception as e:
                self.log_message(f"创建funds.txt失败: {str(e)}", "error")
        else:
            self.log_message(f"找到funds.txt文件: {self.funds_file}")
    
    def run_report(self):
        """运行报告生成任务"""
        # 检查是否选择了任何推送方式
        mobile_enabled = self.mobile_cb.isChecked()
        pc_enabled = self.pc_cb.isChecked()
        
        if not mobile_enabled and not pc_enabled:
            self.log_message("您尚未勾选任何推送方式", "warning")
            return
        
        # 检查手机端推送配置完整性
        if mobile_enabled:
            # 检查是否选择了推送方式
            if not (self.bark_cb.isChecked() or self.gotify_cb.isChecked() or self.wecom_cb.isChecked()):
                self.log_message("请至少选择一种手机推送方式（Bark、Gotify或企业微信）", "warning")
                return
            
            # 检查Bark配置（如果启用）
            if self.bark_cb.isChecked():
                bark_url = self.config.get('advanced', 'bark_url', fallback='')
                bark_token = self.config.get('advanced', 'bark_token', fallback='')
                if not bark_url or not bark_token:
                    self.log_message("Bark配置不完整，请填写服务器地址和设备密钥", "warning")
                    return
            
            # 检查Gotify配置（如果启用）
            if self.gotify_cb.isChecked():
                gotify_url = self.config.get('advanced', 'gotify_url', fallback='')
                gotify_token = self.config.get('advanced', 'gotify_token', fallback='')
                if not gotify_url or not gotify_token:
                    self.log_message("Gotify配置不完整，请填写服务器地址和应用Token", "warning")
                    return
            
            # 检查企业微信配置（如果启用）
            if self.wecom_cb.isChecked():
                if not self.check_wecom_config():
                    self.log_message("企业微信配置不完整，无法进行手机端推送", "warning")
                    return
        
        # 检查PC端报告配置完整性
        if pc_enabled:
            if not self.by_fund_cb.isChecked() and not self.by_user_cb.isChecked():
                self.log_message("请至少选择一种PC报告生成方式（按基金分类或按客户分类）", "warning")
                return
        
        # 保存当前配置（仅在用户操作时创建配置文件）
        self.save_config()
        
        # 创建并启动工作线程
        self.worker = ReportWorker(
            self.config,
            self.base_dir,
            mobile_enabled,
            pc_enabled,
            self.by_fund_cb.isChecked(),
            self.by_user_cb.isChecked()
        )
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished.connect(self.on_report_finished)
        
        # 禁用按钮防止重复点击
        self.run_btn.setEnabled(False)
        self.run_btn.setText("处理中...")
        
        self.worker.start()
    
    def check_wecom_config(self):
        """检查企业微信配置是否完整"""
        wecom_corpid = self.config.get('advanced', 'wecom_corpid', fallback='')
        wecom_agentid = self.config.get('advanced', 'wecom_agentid', fallback='')
        wecom_secret = self.config.get('advanced', 'wecom_secret', fallback='')
        wecom_proxy_url = self.config.get('advanced', 'wecom_proxy_url', fallback='')
        
        if not wecom_corpid or not wecom_agentid or not wecom_secret or not wecom_proxy_url:
            return False
        return True
    
    def on_report_finished(self):
        """报告生成完成后的处理"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("生成并推送报告")
        self.log_message("报告生成任务已完成", "success")

# 高级配置对话框（使用滚动区域）
class AdvancedConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("高级设置")
        self.setFixedSize(500, 650)  # 增加高度以容纳更多设置项
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # ========== Bark设置 ==========
        bark_group = QGroupBox("Bark 推送设置[IOS]")
        bark_layout = QFormLayout(bark_group)
        bark_layout.setSpacing(8)
        bark_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        self.bark_url = QLineEdit()
        self.bark_url.setPlaceholderText("https://your.bark.server")
        bark_layout.addRow("服务器地址:", self.bark_url)
        
        self.bark_token = QLineEdit()
        self.bark_token.setPlaceholderText("Bark应用Token")
        bark_layout.addRow("应用Token:", self.bark_token)
        
        scroll_layout.addWidget(bark_group)
        
        # ========== Gotify设置 ==========
        gotify_group = QGroupBox("Gotify 推送设置[Android]")
        gotify_layout = QFormLayout(gotify_group)
        gotify_layout.setSpacing(8)
        gotify_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        self.gotify_url = QLineEdit()
        self.gotify_url.setPlaceholderText("https://your.gotify.server")
        gotify_layout.addRow("服务器地址:", self.gotify_url)
        
        self.gotify_token = QLineEdit()
        self.gotify_token.setPlaceholderText("Gotify应用Token")
        gotify_layout.addRow("应用Token:", self.gotify_token)
        
        scroll_layout.addWidget(gotify_group)
        
        # ========== 企业微信设置 ==========
        wecom_group = QGroupBox("企业微信设置")
        wecom_layout = QFormLayout(wecom_group)
        wecom_layout.setSpacing(8)
        wecom_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        self.wecom_corpid = QLineEdit()
        wecom_layout.addRow("企业ID (CorpID):", self.wecom_corpid)
        
        self.wecom_agentid = QLineEdit()
        wecom_layout.addRow("应用ID (AgentID):", self.wecom_agentid)
        
        self.wecom_secret = QLineEdit()
        self.wecom_secret.setEchoMode(QLineEdit.Password)
        wecom_layout.addRow("应用密钥 (Secret):", self.wecom_secret)
        
        self.wecom_proxy_url = QLineEdit()
        wecom_layout.addRow("代理地址 (Proxy URL):", self.wecom_proxy_url)
        
        scroll_layout.addWidget(wecom_group)
        
        # ========== 其他设置 ==========
        other_group = QGroupBox("其他设置")
        other_layout = QFormLayout(other_group)
        other_layout.setSpacing(8)
        other_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        
        self.benchmark_funds = QLineEdit()
        other_layout.addRow("基准基金代码:", self.benchmark_funds)
        
        self.target_return = QDoubleSpinBox()
        self.target_return.setRange(0.0, 100.0)
        self.target_return.setDecimals(2)
        self.target_return.setSuffix("%")
        other_layout.addRow("目标年化收益率:", self.target_return)
        
        self.max_message_bytes = QSpinBox()
        self.max_message_bytes.setRange(500, 4096)
        other_layout.addRow("最大消息长度:", self.max_message_bytes)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        other_layout.addRow("最大重试次数:", self.max_retries)
        
        self.retry_delay = QSpinBox()
        self.retry_delay.setRange(1, 60)
        other_layout.addRow("重试延迟(秒):", self.retry_delay)
        
        scroll_layout.addWidget(other_group)
        
        # 设置滚动区域内容
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)
        
        # 加载配置
        self.load_config()
    
    def load_config(self):
        """加载高级配置"""
        config = self.parent.config
        
        # Bark配置
        self.bark_url.setText(config.get('advanced', 'bark_url', fallback=''))
        self.bark_token.setText(config.get('advanced', 'bark_token', fallback=''))
        
        # Gotify配置
        self.gotify_url.setText(config.get('advanced', 'gotify_url', fallback=''))
        self.gotify_token.setText(config.get('advanced', 'gotify_token', fallback=''))
        
        # 企业微信配置
        self.wecom_corpid.setText(config.get('advanced', 'wecom_corpid', fallback=''))
        self.wecom_agentid.setText(config.get('advanced', 'wecom_agentid', fallback=''))
        self.wecom_secret.setText(config.get('advanced', 'wecom_secret', fallback=''))
        self.wecom_proxy_url.setText(config.get('advanced', 'wecom_proxy_url', fallback=''))
        
        # 其他配置
        self.benchmark_funds.setText(config.get('advanced', 'benchmark_funds', fallback=''))
        self.target_return.setValue(config.getfloat('advanced', 'target_return', fallback=5.0))
        self.max_message_bytes.setValue(config.getint('advanced', 'max_message_bytes', fallback=2048))
        self.max_retries.setValue(config.getint('advanced', 'max_retries', fallback=3))
        self.retry_delay.setValue(config.getint('advanced', 'retry_delay', fallback=5))
    
    def accept(self):
        """保存配置并关闭对话框"""
        # 保存配置到父窗口的config对象
        self.parent.config['advanced'] = {
            'bark_url': self.bark_url.text(),
            'bark_token': self.bark_token.text(),
            'gotify_url': self.gotify_url.text(),
            'gotify_token': self.gotify_token.text(),
            'wecom_corpid': self.wecom_corpid.text(),
            'wecom_agentid': self.wecom_agentid.text(),
            'wecom_secret': self.wecom_secret.text(),
            'wecom_proxy_url': self.wecom_proxy_url.text(),
            'benchmark_funds': self.benchmark_funds.text(),
            'target_return': str(self.target_return.value()),
            'max_message_bytes': str(self.max_message_bytes.value()),
            'max_retries': str(self.max_retries.value()),
            'retry_delay': str(self.retry_delay.value())
        }
        
        self.parent.log_message("高级配置已保存")
        super().accept()

# 报告工作线程
class ReportWorker(QThread):
    log_signal = pyqtSignal(str, str)  # 消息, 级别
    finished = pyqtSignal()
    
    def __init__(self, config, base_dir, mobile_enabled, pc_enabled, by_fund, by_user):
        super().__init__()
        self.config = config
        self.base_dir = base_dir
        self.mobile_enabled = mobile_enabled
        self.pc_enabled = pc_enabled
        self.by_fund = by_fund
        self.by_user = by_user
        self.fund_data = {}  # 存储基金数据
        self.config_dir = os.path.join(base_dir, "config")
        self.funds_file = os.path.join(self.config_dir, "funds.txt")
        self.report_dir = os.path.join(base_dir, "report")
        self.target_return = config.getfloat('advanced', 'target_return', fallback=5.0)
        self.max_message_bytes = config.getint('advanced', 'max_message_bytes', fallback=2048)
        self.max_retries = config.getint('advanced', 'max_retries', fallback=3)
        self.retry_delay = config.getint('advanced', 'retry_delay', fallback=5)
    
    def get_number_emoji(self, number):
        """数字转序号emoji"""
        number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣',
                        '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        return number_emojis[number-1] if 1 <= number <= 10 else f'{number}.'
    
    def split_long_content(self, content, max_bytes=None):
        """智能分割长内容"""
        if max_bytes is None:
            max_bytes = self.max_message_bytes
        
        chunks = []
        current_chunk = []
        current_bytes = 0
        
        for line in content.split('\n'):
            line_bytes = line.encode('utf-8')
            line_length = len(line_bytes) + 1  # 包含换行符
            
            if current_bytes + line_length > max_bytes:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_bytes = 0
                
            current_chunk.append(line)
            current_bytes += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def get_fund_info(self, code):
        """获取基金信息（三接口冗余查询）"""
        # 接口1: fundgz.1234567.com.cn
        try:
            url1 = f"http://fundgz.1234567.com.cn/js/{code}.js"
            response1 = requests.get(url1, headers={'Referer': 'http://fundf10.eastmoney.com/'}, timeout=10)
            response1.raise_for_status()
            
            if "jsonpgz" in response1.text:
                json_str = re.sub(r'^jsonpgz\(|\);$', '', response1.text)
                fund_data = json.loads(json_str)
                return {
                    'code': fund_data['fundcode'],
                    'name': fund_data['name'],
                    'nav_date': fund_data['jzrq'],
                    'nav': float(fund_data['dwjz']),
                    'change': fund_data.get('jzzl', 'N/A'),
                    'valid': True,
                    'source': 1
                }
        except:
            pass
        
        # 接口2: j4.esongfund.com
        try:
            url2 = f"https://j4.esongfund.com/eap/api/fund/public/portal/fundDetail/getFundBaseInfo?fundCode={code}"
            response2 = requests.get(url2, headers={'Referer': 'http://fundf10.eastmoney.com/'}, timeout=10)
            response2.raise_for_status()
            data = response2.json()
            
            if data['code'] == 200:
                info = data['data']
                return {
                    'code': code,
                    'name': info['fundName'],
                    'nav_date': info['netValueDate'],
                    'nav': float(info['netValue']),
                    'change': info['dayGrowth'],
                    'valid': True,
                    'source': 2
                }
        except:
            pass
        
        # 接口3: fund.eastmoney.com/pingzhongdata
        try:
            url3 = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
            response3 = requests.get(url3, headers={'Referer': 'http://fundf10.eastmoney.com/'}, timeout=10)
            response3.encoding = 'utf-8'  # 显式设置编码
            response3.raise_for_status()
            js_content = response3.text
            
            # 提取基金名称
            name_match = re.search(r'var fS_name\s*=\s*"([^"]+)"', js_content)
            fund_name = name_match.group(1) if name_match else f"查询失败({code})"
            
            # 提取净值数据
            nav_data_match = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\])', js_content)
            if nav_data_match:
                nav_data = json.loads(nav_data_match.group(1))
                if nav_data:
                    # 获取最新净值数据点
                    latest_point = nav_data[-1]
                    nav_timestamp = latest_point['x'] / 1000
                    nav_date = datetime.fromtimestamp(nav_timestamp).strftime('%Y-%m-%d')
                    nav_value = latest_point['y']
                    
                    # 检查净值日期是否超过当前日期
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    if nav_date > current_date:
                        # 尝试使用前一个净值点
                        if len(nav_data) > 1:
                            prev_point = nav_data[-2]
                            nav_timestamp = prev_point['x'] / 1000
                            nav_date = datetime.fromtimestamp(nav_timestamp).strftime('%Y-%m-%d')
                            nav_value = prev_point['y']
                        else:
                            return {
                                'code': code,
                                'name': fund_name + " [未开放]",
                                'nav_date': "",
                                'nav': 0.0,
                                'change': "N/A",
                                'valid': False,
                                'source': 3
                            }
                    
                    # 提取涨跌幅
                    change_match = re.search(r'var syl_1y\s*=\s*"([^"]*)"', js_content)
                    change_value = change_match.group(1) if change_match else "N/A"
                    
                    return {
                        'code': code,
                        'name': fund_name + " [未开放]",
                        'nav_date': nav_date,
                        'nav': float(nav_value),
                        'change': change_value,
                        'valid': True,
                        'source': 3
                    }
        except Exception as e:
            pass
        
        # 所有接口都失败时返回未知基金信息
        return {
            'code': code,
            'name': f"查询失败({code})",
            'nav_date': "",
            'nav': 0.0,
            'change': "N/A",
            'valid': False,
            'source': 0
        }
    
    def calculate_returns(self, buy_date_str, nav_date_str, profit, amount, is_valid=True):
        """计算收益率"""
        if not is_valid:
            return ("未知", "未知")
        
        try:
            buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d")
            nav_date = datetime.strptime(nav_date_str, "%Y-%m-%d")
            
            if nav_date < buy_date:
                return ("N/A", "N/A")
                
            delta = nav_date - buy_date
            days = delta.days
            
            if days <= 0 or amount == 0:
                return ("N/A", "N/A")
            
            absolute_return = (profit / float(amount)) * 100
            years = days / 365
            annualized_return = (absolute_return / years) if years > 0 else "N/A"
            
            return (
                f"{absolute_return:+.2f}%",
                f"{annualized_return:+.2f}%" if isinstance(annualized_return, float) else "N/A"
            )
        except:
            return ("N/A", "N/A")
    
    def validate_fund_row(self, row, line_num):
        """验证数据行有效性"""
        if len(row) != 5:
            return False
        
        username, code, buy_date, amount, shares = row
        if not re.match(r'^[\u4e00-\u9fa5A-Za-z]{2,20}$', username):
            return False
        
        try:
            datetime.strptime(buy_date, '%Y-%m-%d')
            float(amount)
            float(shares)
        except ValueError:
            return False
        
        return True
    
    def generate_user_report(self, user, data, emoji):
        """生成用户报告（用于推送）"""
        # 对基金进行排序：先有效基金，再无效基金；每组内按购买日期排序
        sorted_funds = sorted(
            data['funds'], 
            key=lambda x: (
                not x.get('valid', True),  # 有效基金排前面
                datetime.strptime(x['buy_date'], "%Y-%m-%d")  # 按购买日期排序
            )
        )
        
        report = [
            f"{emoji} {user} 持仓详情:{len(data['funds'])}支",
            "▔▔▔▔▔▔▔▔▔▔▔▔▔▔"
        ]
        
        for idx, fund in enumerate(sorted_funds, 1):
            # 处理基金名称显示（保留[未开放]标记）
            fund_title = f"{self.get_number_emoji(idx)} {fund['name']} | {fund['code']}"
            
            report.append(fund_title)
            report.append(f"├ 购买日期:{fund['buy_date']}")
            report.append(f"├ 购买金额:{fund['buy_amount']/10000:.2f}万")
            
            if fund.get('valid', True) and fund.get('nav_date'):
                # 将日期格式从 "YYYY-MM-DD" 转换为 "MM-DD"
                nav_date = datetime.strptime(fund['nav_date'], "%Y-%m-%d").strftime("%m-%d")
                report.append(f"├ 最新净值:{fund['nav']:.4f} | {nav_date}")
            else:
                report.append(f"├ 最新净值:未知")
            
            if fund.get('valid', True) and 'profit' in fund:
                report.append(f"├ 持仓收益:{fund['profit']:+,.2f}")
            else:
                report.append(f"├ 持仓收益:未知")
            
            if fund.get('valid', True) and 'returns' in fund:
                report.append(f"└ 收益率:{fund['returns']['annualized']}")
            else:
                report.append(f"└ 收益率:未知")
        
        return '\n'.join(report)
    
    def generate_performance_summary(self, user_data, target_return, time_str, failed_users=None):
        """生成业绩达标总结报告（用于推送）"""
        # 收集所有达到目标收益率的基金
        performance_data = defaultdict(list)
        
        for user, data in user_data.items():
            for fund in data['funds']:
                # 只处理有效基金
                if not fund.get('valid', True) or 'returns' not in fund:
                    continue
                    
                # 提取年化收益率数值
                try:
                    if fund['returns']['annualized'] in ["N/A", "未知"]:
                        continue
                        
                    # 从字符串中提取数字部分（保留符号）
                    return_str = fund['returns']['annualized'].rstrip('%')
                    if return_str.startswith('+'):
                        return_value = float(return_str[1:])
                    elif return_str.startswith('-'):
                        return_value = float(return_str)  # 保留负号
                    else:
                        return_value = float(return_str)
                    
                    # 检查是否达标（正收益且大于等于目标值）
                    if return_value >= target_return:
                        performance_data[user].append({
                            'code': fund['code'],
                            'name': fund['name'],
                            'annualized': return_value
                        })
                except (ValueError, TypeError) as e:
                    continue
        
        # 生成报告内容
        if not performance_data:
            report = [
                f"📊 业绩达标总结(≥{target_return}%)",
                "▔▔▔▔▔▔▔▔▔▔▔▔▔▔",
                "今日无达标基金"
            ]
        else:
            report = [
                f"📊 业绩达标总结(≥{target_return}%)",
                "▔▔▔▔▔▔▔▔▔▔▔▔▔▔"
            ]
            
            for user, funds in performance_data.items():
                report.append(f"👤 {user}:")
                for fund in funds:
                    report.append(f"  · {fund['name']} ({fund['code']}): {fund['annualized']:.2f}%")
                report.append("")  # 添加空行分隔不同用户
        
        # 添加失败用户提示
        if failed_users:
            report.append("⚠️ 报告推送异常:")
            report.append(f"以下{len(failed_users)}位用户报告未成功推送:")
            report.append(", ".join(failed_users))
            report.append("请检查网络连接或手动处理")
        
        report.append(f"⏰ 报告生成: {time_str}")
        return '\n'.join(report)
    
    def generate_fund_report(self, fund_code, fund_name, holdings):
        """生成基金报告：持有该基金的客户情况列表和详情"""
        # 清洁基金名称（去除[未开放]标记）
        clean_fund_name = fund_name.replace(" [未开放]", "")
        
        # 按客户分组并排序（按最早购买日期）
        user_holdings = defaultdict(list)
        for holding in holdings:
            user_holdings[holding['username']].append(holding)
        
        # 按每个客户最早购买该基金的日期排序
        sorted_users = []
        for user, funds in user_holdings.items():
            # 获取该用户的最早购买日期
            earliest_date = min([datetime.strptime(f['buy_date'], "%Y-%m-%d") for f in funds])
            sorted_users.append((user, earliest_date))
        
        # 按最早购买日期排序
        sorted_users.sort(key=lambda x: x[1])
        
        # 生成报告 - 使用简单字符避免乱码
        report = [
            f"基金报告: {clean_fund_name} ({fund_code})",
            "=" * 50,
            f"持有客户数: {len(user_holdings)}人 | 总持仓数: {len(holdings)}笔",
            ""
        ]
        
        # 添加汇总统计
        total_amount = sum(h['buy_amount'] for h in holdings)
        total_profit = sum(h['profit'] for h in holdings if h.get('valid', True))
        report.append(f"总买入金额: {total_amount:,.2f}元")
        report.append(f"总持仓收益: {total_profit:+,.2f}元")
        report.append("")
        
        # 添加每个客户的持有详情（按购买时间排序）
        for user, _ in sorted_users:
            funds = user_holdings[user]
            
            # 按购买日期排序
            sorted_funds = sorted(funds, key=lambda x: datetime.strptime(x['buy_date'], "%Y-%m-%d"))
            
            report.append(f"客户: {user}")
            report.append("-" * 30)
            
            for fund in sorted_funds:
                report.append(f"购买日期: {fund['buy_date']}")
                report.append(f"买入金额: {fund['buy_amount']:,.2f}元")
                
                if fund.get('valid', True) and fund.get('nav_date'):
                    # 将净值日期格式化为MM-DD
                    nav_date = datetime.strptime(fund['nav_date'], "%Y-%m-%d").strftime("%m-%d")
                    report.append(f"最新净值: {fund['nav']:.4f} ({nav_date})")
                    report.append(f"持仓收益: {fund['profit']:+,.2f}")
                    report.append(f"收益率: {fund['returns_annualized']}")
                else:
                    report.append(f"最新净值: 未知")
                    report.append(f"持仓收益: 未知")
                    report.append(f"收益率: 未知")
                
                report.append("")  # 添加空行分隔不同购买记录
            
            if user != sorted_users[-1][0]:
                report.append("\n")  # 用户间分隔线（最后一个用户不加）
        
        return '\n'.join(report)
    
    def sanitize_filename(self, name):
        """清洗文件名中的非法字符"""
        # 替换特殊字符和空格
        name = re.sub(r'[\\/*?:"<>|]', '_', name)
        # 替换中英文括号
        name = name.replace('(', '_').replace(')', '_')
        name = name.replace('（', '_').replace('）', '_')
        # 替换空格
        name = name.replace(' ', '_')
        return name.strip()
    
    def send_bark_notification(self, title, message, retries=None):
        """发送Bark通知（带重试机制）"""
        if retries is None:
            retries = self.max_retries
            
        attempts = 0
        while attempts <= retries:
            attempts += 1
            try:
                bark_url = self.config.get('advanced', 'bark_url', fallback='')
                bark_token = self.config.get('advanced', 'bark_token', fallback='')
                
                if not bark_url or not bark_token:
                    self.log_signal.emit("Bark配置不完整，无法发送通知", "error")
                    return False
                
                # 修复：使用查询参数而不是路径参数
                # 对标题和消息进行URL编码
                encoded_title = quote(title, safe='')
                encoded_message = quote(message, safe='')
                
                # 构建请求URL - 使用查询参数
                url = f"{bark_url}/{bark_token}?title={encoded_title}&body={encoded_message}"
                
                # 发送请求
                response = requests.get(url, verify=False, timeout=10)
                
                if response.status_code == 200:
                    self.log_signal.emit(f"Bark通知发送成功: {title[:20]}...", "success")
                    return True
                else:
                    self.log_signal.emit(f"Bark通知发送失败: {response.status_code}", "error")
                    self.log_signal.emit(f"响应内容: {response.text[:100]}", "error")
                    raise Exception(f"HTTP状态码: {response.status_code}")
            except Exception as e:
                error_msg = str(e)
                self.log_signal.emit(f"Bark通知发送异常(尝试 {attempts}/{retries}): {error_msg}", "warning")
                
                if attempts <= retries:
                    time.sleep(self.retry_delay)
                else:
                    self.log_signal.emit(f"⚠️ Bark推送失败: {title[:20]}...", "error")
                    return False
    
    def send_gotify_notification(self, title, message, retries=None):
        """发送Gotify通知（带重试机制）"""
        if retries is None:
            retries = self.max_retries
            
        attempts = 0
        while attempts <= retries:
            attempts += 1
            try:
                gotify_url = self.config.get('advanced', 'gotify_url', fallback='')
                gotify_token = self.config.get('advanced', 'gotify_token', fallback='')
                
                if not gotify_url or not gotify_token:
                    self.log_signal.emit("Gotify配置不完整，无法发送通知", "error")
                    return False
                
                # 构建请求URL
                url = f"{gotify_url}/message?token={gotify_token}"
                
                # 构建请求数据
                data = {
                    "title": title,
                    "message": message,
                    "priority": 5
                }
                
                # 发送请求
                response = requests.post(url, json=data, verify=False, timeout=10)
                
                if response.status_code == 200:
                    self.log_signal.emit(f"Gotify通知发送成功: {title[:20]}...", "success")
                    return True
                else:
                    self.log_signal.emit(f"Gotify通知发送失败: {response.status_code}", "error")
                    self.log_signal.emit(f"响应内容: {response.text[:100]}", "error")
                    raise Exception(f"HTTP状态码: {response.status_code}")
            except Exception as e:
                error_msg = str(e)
                self.log_signal.emit(f"Gotify通知发送异常(尝试 {attempts}/{retries}): {error_msg}", "warning")
                
                if attempts <= retries:
                    time.sleep(self.retry_delay)
                else:
                    self.log_signal.emit(f"⚠️ Gotify推送失败: {title[:20]}...", "error")
                    return False
    
    def send_wecom_notification(self, title, message, retries=None):
        """发送企业微信通知（带重试机制）"""
        if retries is None:
            retries = self.max_retries
            
        attempts = 0
        while attempts <= retries:
            attempts += 1
            try:
                wecom_corpid = self.config.get('advanced', 'wecom_corpid', fallback='')
                wecom_agentid = self.config.get('advanced', 'wecom_agentid', fallback='')
                wecom_secret = self.config.get('advanced', 'wecom_secret', fallback='')
                wecom_proxy_url = self.config.get('advanced', 'wecom_proxy_url', fallback='')
                
                if not wecom_corpid or not wecom_agentid or not wecom_secret or not wecom_proxy_url:
                    self.log_signal.emit("企业微信配置不完整，无法发送通知", "error")
                    return False
                
                # 获取access_token
                token_url = f"{wecom_proxy_url}/cgi-bin/gettoken?corpid={wecom_corpid}&corpsecret={wecom_secret}"
                token_response = requests.get(token_url, timeout=10)
                token_data = token_response.json()
                
                if token_data.get('errcode') != 0:
                    raise Exception(f"Token获取失败: {token_data.get('errmsg')}")
                
                access_token = token_data.get('access_token')
                
                # 构建消息数据
                msg_data = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": wecom_agentid,
                    "text": {
                        "content": f"{title}\n\n{message}"
                    },
                    "safe": 0
                }
                
                # 通过代理发送消息
                send_url = f"{wecom_proxy_url}/cgi-bin/message/send?access_token={access_token}"
                send_response = requests.post(send_url, json=msg_data, timeout=10)
                send_data = send_response.json()
                
                if send_data.get('errcode') == 0:
                    self.log_signal.emit(f"企业微信通知发送成功: {title[:20]}...", "success")
                    return True
                else:
                    self.log_signal.emit(f"企业微信通知发送失败: {send_data.get('errmsg')}", "error")
                    raise Exception(f"API错误: {send_data.get('errmsg')}")
            except Exception as e:
                error_msg = str(e)
                self.log_signal.emit(f"企业微信通知发送异常(尝试 {attempts}/{retries}): {error_msg}", "warning")
                
                if attempts <= retries:
                    time.sleep(self.retry_delay)
                else:
                    self.log_signal.emit(f"⚠️ 企业微信推送失败: {title[:20]}...", "error")
                    return False
    
    def run(self):
        try:
            # 开始生成基金报告
            self.log_signal.emit("开始生成基金报告...", "info")
            
            # 确保报告目录存在
            os.makedirs(self.report_dir, exist_ok=True)
            
            # 读取基金数据
            if not os.path.exists(self.funds_file):
                self.log_signal.emit(f"错误: 未找到{self.funds_file}文件", "error")
                return
            
            self.log_signal.emit(f"读取基金数据文件: {self.funds_file}", "info")
            
            # 解析基金数据
            holdings = []
            user_data = OrderedDict()  # 使用有序字典保持用户顺序
            fund_holdings = defaultdict(list)  # 按基金存储持有情况
            
            with open(self.funds_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for line_num, row in enumerate(reader, 1):
                    # 跳过空行和注释行
                    if not row or not row[0] or row[0].startswith('#'):
                        continue
                    
                    # 验证数据行有效性
                    if not self.validate_fund_row(row, line_num):
                        self.log_signal.emit(f"跳过无效行 {line_num}: {','.join(row)}", "warning")
                        continue
                    
                    username, code, buy_date, amount, shares = row
                    
                    # 确保用户数据存在
                    if username not in user_data:
                        user_data[username] = {'funds': []}
                    
                    # 获取基金信息（如果尚未获取）
                    if code not in self.fund_data:
                        self.fund_data[code] = self.get_fund_info(code)
                    
                    fund_info = self.fund_data[code]
                    
                    # 计算收益
                    buy_amount = float(amount)
                    if fund_info.get('valid', True) and fund_info.get('nav_date'):
                        current_value = float(shares) * fund_info['nav']
                        profit = current_value - buy_amount
                        is_valid = True
                    else:
                        current_value = 0
                        profit = 0
                        is_valid = False
                    
                    abs_return, ann_return = self.calculate_returns(
                        buy_date, 
                        fund_info.get('nav_date', ''),
                        profit,
                        buy_amount,
                        is_valid
                    )
                    
                    # 存储用户数据
                    fund_data = {
                        'code': code,
                        'name': fund_info['name'],
                        'buy_date': buy_date,
                        'buy_amount': buy_amount,
                        'nav': fund_info['nav'],
                        'nav_date': fund_info.get('nav_date', ''),
                        'profit': profit,
                        'returns': {
                            'absolute': abs_return,
                            'annualized': ann_return
                        },
                        'valid': is_valid
                    }
                    user_data[username]['funds'].append(fund_data)
                    
                    # 存储基金持有情况（用于生成基金报告）
                    fund_holdings[code].append({
                        'username': username,
                        'buy_date': buy_date,
                        'buy_amount': buy_amount,
                        'shares': float(shares),
                        'nav': fund_info['nav'],
                        'nav_date': fund_info.get('nav_date', ''),
                        'profit': profit,
                        'returns_absolute': abs_return,
                        'returns_annualized': ann_return,
                        'valid': is_valid,
                        'fund_name': fund_info['name']  # 存储原始基金名称
                    })
            
            self.log_signal.emit(f"解析到 {len(holdings)} 条持仓记录", "info")
            
            # 手机端推送
            if self.mobile_enabled:
                bark_enabled = self.config.getboolean('mobile', 'bark_enabled', fallback=False)
                gotify_enabled = self.config.getboolean('mobile', 'gotify_enabled', fallback=False)
                wecom_enabled = self.config.getboolean('mobile', 'wecom_enabled', fallback=False)
                
                # 生成所有客户报告
                user_reports = []
                user_emojis = ['👤','👥']  # 用户标识符
                for idx, (user, data) in enumerate(user_data.items()):
                    user_emoji = user_emojis[idx % len(user_emojis)]
                    report_content = self.generate_user_report(user, data, user_emoji)
                    user_reports.append({
                        'user': user,
                        'content': report_content
                    })
                
                # 生成业绩达标总结报告
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                performance_report = self.generate_performance_summary(
                    user_data, 
                    self.target_return, 
                    time_str
                )
                
                # 推送所有客户报告
                failed_users = []
                for report in user_reports:
                    user = report['user']
                    report_chunks = self.split_long_content(report['content'])
                    total_pages = len(report_chunks)
                    
                    # 推送该用户的所有分片
                    all_chunks_success = True
                    for page_num, chunk in enumerate(report_chunks, 1):
                        title = f"净值推送报告[{page_num}/{total_pages}]"
                        
                        # 根据配置选择推送方式
                        success = False
                        if bark_enabled:
                            success = self.send_bark_notification(title, chunk)
                        if gotify_enabled and not success:  # 如果Bark失败尝试Gotify
                            success = self.send_gotify_notification(title, chunk)
                        if wecom_enabled and not success:  # 如果前两者失败尝试企业微信
                            success = self.send_wecom_notification(title, chunk)
                        
                        if not success:
                            all_chunks_success = False
                            break
                        
                        time.sleep(0.5)  # 避免消息发送过快
                    
                    # 记录用户推送状态
                    if not all_chunks_success:
                        failed_users.append(user)
                        self.log_signal.emit(f"⚠️ 用户 {user} 报告推送失败", "warning")
                
                # 推送业绩总结报告
                perf_chunks = self.split_long_content(performance_report)
                total_pages = len(perf_chunks)
                
                for page_num, chunk in enumerate(perf_chunks, 1):
                    title = f"业绩达标总结[{page_num}/{total_pages}]"
                    
                    # 根据配置选择推送方式
                    success = False
                    if bark_enabled:
                        success = self.send_bark_notification(title, chunk)
                    if gotify_enabled and not success:
                        success = self.send_gotify_notification(title, chunk)
                    if wecom_enabled and not success:
                        success = self.send_wecom_notification(title, chunk)
                    
                    time.sleep(0.5)
                
                # 最终状态报告
                success_count = len(user_data) - len(failed_users)
                self.log_signal.emit(f"客户报告推送: {success_count}成功, {len(failed_users)}失败", "success")
            
            # PC端报告生成
            if self.pc_enabled:
                # 获取当前时间戳（用于创建日期目录）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 按基金分类生成报告
                if self.by_fund:
                    # 生成每个基金的报告
                    for code, holdings_list in fund_holdings.items():
                        fund_name = self.fund_data.get(code, {}).get('name', f"基金{code}")
                        
                        # 创建基金目录
                        fund_safe_name = self.sanitize_filename(f"{code}_{fund_name}")
                        fund_dir = os.path.join(self.report_dir, "by_fund", fund_safe_name)
                        
                        if not os.path.exists(fund_dir):
                            os.makedirs(fund_dir, exist_ok=True)
                        
                        # 生成报告内容
                        report_content = self.generate_fund_report(code, fund_name, holdings_list)
                        
                        # 保存报告 - 直接使用时间戳作为文件名
                        file_name = f"{timestamp}.txt"
                        file_path = os.path.join(fund_dir, file_name)
                        
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(report_content)
                            self.log_signal.emit(f"已保存基金报告: {file_path}", "info")
                        except Exception as e:
                            self.log_signal.emit(f"保存基金报告失败: {str(e)}", "error")
                
                # 按客户分类生成报告
                if self.by_user:
                    # 生成每个用户的报告
                    for user, funds_list in user_data.items():
                        # 创建用户目录
                        user_safe_name = self.sanitize_filename(user)
                        user_dir = os.path.join(self.report_dir, "by_user", user_safe_name)
                        
                        if not os.path.exists(user_dir):
                            os.makedirs(user_dir, exist_ok=True)
                        
                        # 生成报告内容
                        report_content = ""
                        for fund in funds_list['funds']:
                            report_content += f"基金代码: {fund['code']}\n"
                            report_content += f"基金名称: {fund['name']}\n"
                            report_content += f"购买日期: {fund['buy_date']}\n"
                            report_content += f"购买金额: {fund['buy_amount']:,.2f}\n"
                            if fund.get('valid', True):
                                report_content += f"最新净值: {fund['nav']:.4f} ({fund['nav_date']})\n"
                                report_content += f"持仓收益: {fund['profit']:+,.2f}\n"
                                report_content += f"年化收益率: {fund['returns']['annualized']}\n"
                            else:
                                report_content += "最新净值: 未知\n"
                                report_content += "持仓收益: 未知\n"
                                report_content += "年化收益率: 未知\n"
                            report_content += "\n"
                        
                        # 保存报告 - 直接使用时间戳作为文件名
                        file_name = f"{timestamp}.txt"
                        file_path = os.path.join(user_dir, file_name)
                        
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(report_content)
                            self.log_signal.emit(f"已保存客户报告: {file_path}", "info")
                        except Exception as e:
                            self.log_signal.emit(f"保存客户报告失败: {str(e)}", "error")
                
                # ========== 生成目标收益报告 ==========
                target_report_content = self.generate_performance_summary(
                    user_data, 
                    self.target_return, 
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                )
                target_report_path = os.path.join(self.report_dir, "已达目标收益.txt")
                
                try:
                    with open(target_report_path, 'w', encoding='utf-8') as f:
                        f.write(target_report_content)
                    self.log_signal.emit(f"已保存目标收益报告: {target_report_path}", "success")
                except Exception as e:
                    self.log_signal.emit(f"保存目标收益报告失败: {str(e)}", "error")
                
                self.log_signal.emit("PC端报告生成完成", "success")
                self.log_signal.emit(f"报告保存位置: {os.path.abspath(self.report_dir)}", "info")
            
            self.log_signal.emit("报告生成和推送完成", "success")
            
        except Exception as e:
            self.log_signal.emit(f"报告生成失败: {str(e)}", "error")
        finally:
            self.finished.emit()

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = FundReportSystem()
    window.show()
    
    sys.exit(app.exec_())