#!/usr/bin/env python3
"""
环境检查脚本
用于诊断Node.js和npm安装问题
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n🔍 检查 {description}...")
    print(f"命令: {' '.join(command) if isinstance(command, list) else command}")
    
    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ 成功: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 失败 (退出代码: {result.returncode})")
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
        return False
    except FileNotFoundError:
        print("❌ 命令未找到")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def check_path():
    """检查PATH环境变量"""
    print("\n📁 PATH环境变量:")
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    node_paths = []
    
    for path_dir in path_dirs:
        if 'node' in path_dir.lower() or 'npm' in path_dir.lower():
            node_paths.append(path_dir)
            print(f"  ✅ {path_dir}")
    
    if not node_paths:
        print("  ⚠️  在PATH中未找到Node.js相关路径")
    
    # 检查常见的Node.js安装路径
    common_node_paths = []
    if platform.system() == "Windows":
        common_node_paths = [
            r"C:\Program Files\nodejs",
            r"C:\Program Files (x86)\nodejs",
            os.path.expanduser(r"~\AppData\Roaming\npm"),
        ]
    else:
        common_node_paths = [
            "/usr/local/bin",
            "/usr/bin",
            "/opt/node/bin",
            os.path.expanduser("~/.nvm"),
        ]
    
    print("\n📂 检查常见Node.js安装路径:")
    for path in common_node_paths:
        if os.path.exists(path):
            print(f"  ✅ 存在: {path}")
            # 检查是否包含node或npm
            try:
                files = os.listdir(path)
                node_files = [f for f in files if 'node' in f.lower() or 'npm' in f.lower()]
                if node_files:
                    print(f"     包含: {', '.join(node_files[:5])}")
            except:
                pass
        else:
            print(f"  ❌ 不存在: {path}")

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 YOLO检测系统环境诊断工具")
    print("=" * 60)
    
    print(f"\n💻 系统信息:")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print(f"  Python版本: {sys.version}")
    
    # 检查Python
    python_ok = run_command([sys.executable, "--version"], "Python")
    
    # 检查pip
    pip_ok = run_command([sys.executable, "-m", "pip", "--version"], "pip")
    
    # 检查Node.js的多种可能命令
    node_commands = ['node', 'nodejs']
    node_ok = False
    
    for cmd in node_commands:
        if run_command([cmd, "--version"], f"Node.js ({cmd})"):
            node_ok = True
            break
    
    # 检查npm
    npm_ok = run_command(["npm", "--version"], "npm")
    
    # 检查npx
    npx_ok = run_command(["npx", "--version"], "npx")
    
    # 检查PATH
    check_path()
    
    # 检查项目文件
    print("\n📋 项目文件检查:")
    required_files = [
        "app.py",
        "requirements.txt", 
        "frontend/package.json",
        "frontend/src/main.js"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (缺失)")
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 诊断总结:")
    print("=" * 60)
    
    if python_ok:
        print("✅ Python环境正常")
    else:
        print("❌ Python环境有问题")
    
    if node_ok:
        print("✅ Node.js环境正常")
    else:
        print("❌ Node.js环境有问题")
        print("\n💡 Node.js问题解决建议:")
        print("1. 从官网下载并安装Node.js: https://nodejs.org")
        print("2. 安装后重启命令行/终端")
        print("3. 验证安装: node --version")
        print("4. 确保Node.js已添加到PATH环境变量")
    
    if npm_ok:
        print("✅ npm环境正常")
    else:
        print("❌ npm环境有问题")
        print("\n💡 npm问题解决建议:")
        print("1. npm通常与Node.js一起安装")
        print("2. 如果Node.js已安装但npm不可用，请重新安装Node.js")
        print("3. 检查npm是否在PATH中")
    
    print("\n" + "=" * 60)
    
    if node_ok and npm_ok:
        print("🎉 环境检查通过！可以运行系统了")
        print("\n💡 启动建议:")
        print("- Windows: 双击 start.bat")
        print("- Linux/Mac: python run.py")
    else:
        print("⚠️  环境存在问题，请根据上述建议解决")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断检查")
    except Exception as e:
        print(f"\n❌ 检查过程中出现异常: {e}")
    
    input("\n按回车键退出...") 