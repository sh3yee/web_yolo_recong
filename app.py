from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from ultralytics import YOLO
import base64
import io
from PIL import Image
from datetime import datetime
import json

app = Flask(__name__)

# 更简单但更有效的CORS配置
CORS(app,
     origins="*",  # 允许所有来源
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
     supports_credentials=False)  # 暂时关闭credentials避免复杂性

# 手动添加CORS响应头（双重保险）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'false')
    return response

# 简化的配置 - 使用SQLite数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yolo_detection.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['SECRET_KEY'] = 'yolo-detection-secret-key-2024'

db = SQLAlchemy(app)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# 数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DetectionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    detection_type = db.Column(db.String(20), nullable=False)  # image, video, camera
    original_file = db.Column(db.String(255))
    result_file = db.Column(db.String(255))
    detections = db.Column(db.Text)  # JSON格式的检测结果
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 初始化YOLO模型
model = None
current_model_path = 'yolov8n.pt'  # 当前加载的模型路径

def load_yolo_model(model_path='yolov8n.pt'):
    global model, current_model_path
    try:
        # 使用指定的模型路径
        model = YOLO(model_path)
        current_model_path = model_path
        print(f"✅ YOLO模型加载成功: {model_path}")
        return True
    except Exception as e:
        print(f"❌ YOLO模型加载失败: {e}")
        return False

def get_model_files(directory='models'):
    """获取指定目录下的模型文件列表"""
    model_extensions = ['.pt', '.onnx', '.torchscript']
    model_files = []
    
    # 确保models目录存在
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in model_extensions):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    model_files.append({
                        'name': file,
                        'path': file_path,
                        'relative_path': os.path.relpath(file_path),
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'modified': os.path.getmtime(file_path)
                    })
    except Exception as e:
        print(f"扫描模型文件时出错: {e}")
    
    # 添加预训练模型选项
    pretrained_models = [
        {'name': 'YOLOv8n (Nano)', 'path': 'yolov8n.pt', 'relative_path': 'yolov8n.pt', 'size': 0, 'size_mb': 6.2, 'modified': 0, 'pretrained': True}
    ]
    
    return pretrained_models + model_files

# API路由
@app.route('/api/<path:path>', methods=['OPTIONS'])
def options(path):
    """处理所有API路由的OPTIONS预检请求"""
    return '', 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'success': True,
        'message': 'YOLO检测识别系统运行正常',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user.id,
                'username': user.username
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if User.query.filter_by(username=username).first():
        return jsonify({
            'success': False,
            'message': '用户名已存在'
        }), 400
    
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '注册成功'
    })

@app.route('/api/detect_image', methods=['POST'])
def detect_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id', 1)
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 进行YOLO检测
        try:
            results = model(filepath)
            
            # 处理检测结果
            detections = []
            img = cv2.imread(filepath)
            
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = box.conf[0].cpu().numpy()
                        cls = box.cls[0].cpu().numpy()
                        
                        detections.append({
                            'class': model.names[int(cls)],
                            'confidence': float(conf),
                            'bbox': [float(x1), float(y1), float(x2), float(y2)]
                        })
                        
                        # 在图像上绘制检测框
                        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        cv2.putText(img, f'{model.names[int(cls)]}: {conf:.2f}', 
                                  (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 保存结果图像
            result_filename = 'result_' + filename
            result_filepath = os.path.join('static', result_filename)
            cv2.imwrite(result_filepath, img)
            
            # 保存到数据库
            detection_result = DetectionResult(
                user_id=user_id,
                detection_type='image',
                original_file=filename,
                result_file=result_filename,
                detections=json.dumps(detections),
                confidence=max([d['confidence'] for d in detections]) if detections else 0
            )
            db.session.add(detection_result)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '检测完成',
                'detections': detections,
                'result_image': f'/static/{result_filename}',
                'detection_count': len(detections)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'检测失败: {str(e)}'}), 500
    
    return jsonify({'success': False, 'message': '不支持的文件格式'}), 400

@app.route('/api/detect_video', methods=['POST'])
def detect_video():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id', 1)
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    if file and allowed_video_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        original_name, original_ext = os.path.splitext(filename)
        filename = timestamp + original_name + '.mp4'  # 强制使用.mp4扩展名
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], timestamp + secure_filename(file.filename))
        file.save(filepath)
        
        try:
            # 处理视频检测
            cap = cv2.VideoCapture(filepath)
            
            # 检查视频是否成功打开
            if not cap.isOpened():
                return jsonify({'success': False, 'message': '无法打开视频文件，请检查视频格式'}), 400
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 验证视频参数
            if fps <= 0:
                fps = 25.0  # 默认帧率
            if width <= 0 or height <= 0:
                return jsonify({'success': False, 'message': '视频尺寸无效'}), 400
            
            result_filename = 'result_' + filename
            result_filepath = os.path.join('static', result_filename)
            
            # 使用H.264编码器，确保浏览器兼容性
            # 尝试多种编码器，按优先级排序
            encoders = [
                cv2.VideoWriter_fourcc(*'avc1'),  # H.264 (推荐)
                cv2.VideoWriter_fourcc(*'mp4v'),  # MPEG-4 Part 2
                cv2.VideoWriter_fourcc(*'XVID'),  # Xvid
                cv2.VideoWriter_fourcc(*'MJPG'),  # Motion JPEG (兜底)
            ]
            
            out = None
            for fourcc in encoders:
                try:
                    out = cv2.VideoWriter(result_filepath, fourcc, fps, (width, height))
                    # 测试是否能正确写入
                    if out.isOpened():
                        print(f"✅ 成功使用编码器: {fourcc}")
                        break
                    else:
                        out.release()
                        out = None
                except:
                    if out:
                        out.release()
                        out = None
                    continue
            
            if out is None or not out.isOpened():
                cap.release()
                return jsonify({'success': False, 'message': '无法创建输出视频文件'}), 500
            
            all_detections = []
            frame_count = 0
            processed_frames = 0
            current_detections = []  # 保存当前检测结果，在多帧之间保持
            detection_interval = 10  # 检测间隔帧数
            detection_hold_frames = 30  # 检测结果保持帧数
            last_detection_frame = -detection_hold_frames  # 上次检测的帧号
            
            print(f"📹 开始处理视频: {total_frames} 帧")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 每detection_interval帧检测一次以提高性能
                if frame_count % detection_interval == 0:
                    try:
                        results = model(frame)
                        
                        # 更新上次检测帧号
                        last_detection_frame = frame_count
                        
                        # 清空上一次的检测结果
                        current_detections = []
                        
                        for r in results:
                            boxes = r.boxes
                            if boxes is not None:
                                for box in boxes:
                                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                    conf = box.conf[0].cpu().numpy()
                                    cls = box.cls[0].cpu().numpy()
                                    
                                    detection_info = {
                                        'frame': frame_count,
                                        'class': model.names[int(cls)],
                                        'confidence': float(conf),
                                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                                    }
                                    
                                    # 添加到总检测结果
                                    all_detections.append(detection_info)
                                    
                                    # 添加到当前检测结果（用于绘制）
                                    current_detections.append({
                                        'bbox': [x1, y1, x2, y2],
                                        'class': model.names[int(cls)],
                                        'confidence': conf,
                                        'detection_frame': frame_count
                                    })
                                    
                    except Exception as detection_error:
                        print(f"⚠️  帧 {frame_count} 检测失败: {detection_error}")
                
                # 检查检测结果是否过期（超过保持帧数就清空）
                if frame_count - last_detection_frame > detection_hold_frames:
                    current_detections = []
                
                # 在每一帧上绘制当前的检测结果（保持检测框连续显示）
                for detection in current_detections:
                    x1, y1, x2, y2 = detection['bbox']
                    class_name = detection['class']
                    confidence = detection['confidence']
                    
                    # 根据帧数差异调整透明度（越老越透明）
                    frame_diff = frame_count - detection.get('detection_frame', frame_count)
                    alpha = max(0.3, 1.0 - (frame_diff / detection_hold_frames) * 0.7)
                    
                    # 绘制检测框
                    color = (0, int(255 * alpha), 0)  # 绿色，透明度渐变
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    
                    # 绘制标签背景
                    label = f'{class_name}: {confidence:.2f}'
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    
                    # 标签背景也应用透明度
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (int(x1), int(y1) - label_size[1] - 10), 
                                (int(x1) + label_size[0], int(y1)), color, -1)
                    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                    
                    # 绘制标签文字
                    cv2.putText(frame, label, (int(x1), int(y1) - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
                # 写入帧到输出视频
                out.write(frame)
                frame_count += 1
                processed_frames += 1
                
                # 每处理100帧打印一次进度
                if processed_frames % 100 == 0:
                    progress = (processed_frames / total_frames) * 100 if total_frames > 0 else 0
                    detections_count = len(current_detections)
                    print(f"🎬 处理进度: {progress:.1f}% ({processed_frames}/{total_frames}) - 当前检测: {detections_count}")
                
                # 内存管理：定期清理过期的检测结果
                if frame_count % 500 == 0:
                    current_detections = [d for d in current_detections 
                                        if frame_count - d.get('detection_frame', 0) <= detection_hold_frames]
            
            cap.release()
            out.release()
            
            # 验证输出文件是否存在且有效
            if not os.path.exists(result_filepath):
                return jsonify({'success': False, 'message': '生成视频文件失败'}), 500
            
            file_size = os.path.getsize(result_filepath)
            if file_size < 1024:  # 小于1KB可能是空文件
                return jsonify({'success': False, 'message': '生成的视频文件过小，可能损坏'}), 500
            
            print(f"✅ 视频处理完成: {result_filename} ({file_size} bytes)")
            
            # 保存到数据库
            detection_result = DetectionResult(
                user_id=user_id,
                detection_type='video',
                original_file=os.path.basename(filepath),
                result_file=result_filename,
                detections=json.dumps(all_detections),
                confidence=max([d['confidence'] for d in all_detections]) if all_detections else 0
            )
            db.session.add(detection_result)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '视频检测完成',
                'detections': all_detections,
                'result_video': f'/static/{result_filename}',
                'detection_count': len(all_detections),
                'processed_frames': processed_frames,
                'total_detections': len(all_detections)
            })
            
        except Exception as e:
            print(f"❌ 视频处理异常: {e}")
            return jsonify({'success': False, 'message': f'视频检测失败: {str(e)}'}), 500
    
    return jsonify({'success': False, 'message': '不支持的视频格式'}), 400

@app.route('/api/detect_camera', methods=['POST'])
def detect_camera():
    # 这个接口用于启动摄像头检测
    user_id = request.json.get('user_id', 1)
    
    try:
        # 这里返回摄像头检测的配置信息
        # 实际的摄像头检测会在前端通过WebRTC实现
        return jsonify({
            'success': True,
            'message': '摄像头检测模式已启动',
            'camera_config': {
                'fps': 30,
                'resolution': '640x480'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'摄像头启动失败: {str(e)}'}), 500

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    """处理从前端发送的摄像头帧"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        user_id = data.get('user_id', 1)
        
        # 解码base64图像
        image_data = image_data.split(',')[1]  # 移除data:image/jpeg;base64,前缀
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # 转换为OpenCV格式
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # YOLO检测
        results = model(frame)
        
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = box.cls[0].cpu().numpy()
                    
                    detections.append({
                        'class': model.names[int(cls)],
                        'confidence': float(conf),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })
        
        return jsonify({
            'success': True,
            'detections': detections
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'帧处理失败: {str(e)}'}), 500

@app.route('/api/history/<int:user_id>')
def get_history(user_id):
    """获取用户的检测历史"""
    try:
        results = DetectionResult.query.filter_by(user_id=user_id).order_by(DetectionResult.created_at.desc()).all()
        
        history = []
        for result in results:
            history.append({
                'id': result.id,
                'detection_type': result.detection_type,
                'original_file': result.original_file,
                'result_file': result.result_file,
                'detections': json.loads(result.detections) if result.detections else [],
                'confidence': result.confidence,
                'created_at': result.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取历史记录失败: {str(e)}'}), 500

@app.route('/api/history/delete/<int:record_id>', methods=['DELETE'])
def delete_history_record(record_id):
    """删除单个检测历史记录"""
    try:
        # 查找记录
        record = DetectionResult.query.get(record_id)
        if not record:
            return jsonify({'success': False, 'message': '记录不存在'}), 404
        
        # 删除关联的文件
        if record.result_file:
            result_file_path = os.path.join('static', record.result_file)
            if os.path.exists(result_file_path):
                try:
                    os.remove(result_file_path)
                    print(f"删除结果文件: {result_file_path}")
                except Exception as e:
                    print(f"删除结果文件失败: {e}")
        
        # 删除原始文件（如果存在）
        if record.original_file:
            original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], record.original_file)
            if os.path.exists(original_file_path):
                try:
                    os.remove(original_file_path)
                    print(f"删除原始文件: {original_file_path}")
                except Exception as e:
                    print(f"删除原始文件失败: {e}")
        
        # 删除数据库记录
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '历史记录删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除记录失败: {str(e)}'}), 500

@app.route('/api/history/batch-delete', methods=['DELETE'])
def batch_delete_history():
    """批量删除检测历史记录"""
    try:
        data = request.get_json()
        record_ids = data.get('record_ids', [])
        user_id = data.get('user_id')
        
        if not record_ids:
            return jsonify({'success': False, 'message': '未指定要删除的记录'}), 400
        
        deleted_count = 0
        failed_count = 0
        
        for record_id in record_ids:
            try:
                # 查找记录
                record = DetectionResult.query.filter_by(id=record_id, user_id=user_id).first()
                if not record:
                    failed_count += 1
                    continue
                
                # 删除关联的文件
                if record.result_file:
                    result_file_path = os.path.join('static', record.result_file)
                    if os.path.exists(result_file_path):
                        try:
                            os.remove(result_file_path)
                        except:
                            pass
                
                if record.original_file:
                    original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], record.original_file)
                    if os.path.exists(original_file_path):
                        try:
                            os.remove(original_file_path)
                        except:
                            pass
                
                # 删除数据库记录
                db.session.delete(record)
                deleted_count += 1
                
            except Exception as e:
                print(f"删除记录 {record_id} 失败: {e}")
                failed_count += 1
        
        db.session.commit()
        
        message = f'成功删除 {deleted_count} 条记录'
        if failed_count > 0:
            message += f'，{failed_count} 条记录删除失败'
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'批量删除失败: {str(e)}'}), 500

@app.route('/api/history/clear/<int:user_id>', methods=['DELETE'])
def clear_user_history(user_id):
    """清空用户的所有检测历史"""
    try:
        # 获取用户的所有记录
        records = DetectionResult.query.filter_by(user_id=user_id).all()
        
        if not records:
            return jsonify({'success': True, 'message': '没有需要清空的记录'})
        
        deleted_count = 0
        
        for record in records:
            try:
                # 删除关联的文件
                if record.result_file:
                    result_file_path = os.path.join('static', record.result_file)
                    if os.path.exists(result_file_path):
                        try:
                            os.remove(result_file_path)
                        except:
                            pass
                
                if record.original_file:
                    original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], record.original_file)
                    if os.path.exists(original_file_path):
                        try:
                            os.remove(original_file_path)
                        except:
                            pass
                
                # 删除数据库记录
                db.session.delete(record)
                deleted_count += 1
                
            except Exception as e:
                print(f"删除记录时出错: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功清空所有历史记录，共删除 {deleted_count} 条记录',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'清空历史记录失败: {str(e)}'}), 500

@app.route('/api/models', methods=['GET'])
def get_models():
    """获取可用的模型列表"""
    try:
        models_dir = request.args.get('dir', 'models')
        model_files = get_model_files(models_dir)
        
        return jsonify({
            'success': True,
            'models': model_files,
            'current_model': current_model_path,
            'models_directory': models_dir
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取模型列表失败: {str(e)}'}), 500

@app.route('/api/models/load', methods=['POST'])
def load_model():
    """加载指定的模型"""
    try:
        data = request.get_json()
        model_path = data.get('model_path')
        
        if not model_path:
            return jsonify({'success': False, 'message': '未指定模型路径'}), 400
        
        # 检查模型文件是否存在（对于本地文件）
        if not model_path.startswith('yolov8') and not os.path.exists(model_path):
            return jsonify({'success': False, 'message': f'模型文件不存在: {model_path}'}), 404
        
        # 加载模型
        success = load_yolo_model(model_path)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'模型加载成功: {model_path}',
                'current_model': current_model_path,
                'model_info': {
                    'path': current_model_path,
                    'classes': list(model.names.values()) if model else [],
                    'class_count': len(model.names) if model else 0
                }
            })
        else:
            return jsonify({'success': False, 'message': '模型加载失败'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'加载模型时出错: {str(e)}'}), 500

@app.route('/api/models/current', methods=['GET'])
def get_current_model():
    """获取当前模型信息"""
    try:
        model_info = {
            'path': current_model_path,
            'loaded': model is not None,
            'classes': list(model.names.values()) if model else [],
            'class_count': len(model.names) if model else 0
        }
        
        return jsonify({
            'success': True,
            'model_info': model_info
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取模型信息失败: {str(e)}'}), 500

@app.route('/api/models/upload', methods=['POST'])
def upload_model():
    """上传模型文件到服务器"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        # 检查文件扩展名
        if not allowed_model_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的模型文件格式'}), 400
        
        # 确保models目录存在
        models_dir = 'models'
        os.makedirs(models_dir, exist_ok=True)
        
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        filepath = os.path.join(models_dir, unique_filename)
        
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'message': '模型文件上传成功',
            'file_path': filepath,
            'filename': unique_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传模型失败: {str(e)}'}), 500

@app.route('/api/models/delete', methods=['DELETE'])
def delete_model():
    """删除指定的模型文件"""
    try:
        data = request.get_json()
        model_path = data.get('model_path')
        
        if not model_path:
            return jsonify({'success': False, 'message': '未指定模型路径'}), 400
        
        # 防止删除预训练模型
        if model_path.startswith('yolov8') and not os.path.exists(model_path):
            return jsonify({'success': False, 'message': '不能删除预训练模型'}), 400
        
        # 检查文件是否存在
        if not os.path.exists(model_path):
            return jsonify({'success': False, 'message': '模型文件不存在'}), 404
        
        # 如果是当前使用的模型，不允许删除
        if model_path == current_model_path:
            return jsonify({'success': False, 'message': '不能删除当前正在使用的模型'}), 400
        
        # 删除文件
        os.remove(model_path)
        
        return jsonify({
            'success': True,
            'message': f'模型文件删除成功: {model_path}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除模型失败: {str(e)}'}), 500

@app.route('/static/<filename>')
def static_files(filename):
    return send_file(os.path.join('static', filename))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video_file(filename):
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_model_file(filename):
    """检查是否为支持的模型文件格式"""
    ALLOWED_EXTENSIONS = {'pt', 'onnx', 'torchscript', 'engine'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    # 创建数据库表和初始数据
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员用户
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password='admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ 创建默认管理员用户: admin / admin123")
    
    # 加载YOLO模型
    load_yolo_model()
    
    print("🚀 启动YOLO检测识别系统...")
    print("📊 数据库: SQLite (yolo_detection.db)")
    print("🌐 访问地址: http://localhost:5001")
    print("👤 默认账号: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False) 