<template>
  <div class="detection-container">
    <!-- 检测方式选择（已注释，默认使用图片检测）
    <el-card class="mode-selector" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>检测方式选择</span>
        </div>
      </template>
      
      <el-radio-group v-model="detectionMode" size="large" @change="handleModeChange">
        <el-radio-button label="image">
          <el-icon><Picture /></el-icon>
          图片检测
        </el-radio-button>
        <el-radio-button label="video">
          <el-icon><VideoPlay /></el-icon>
          视频检测
        </el-radio-button>
        <el-radio-button label="camera">
          <el-icon><Camera /></el-icon>
          摄像头检测
        </el-radio-button>
      </el-radio-group>
    </el-card>
    -->

    <el-row :gutter="20">
      <!-- 左侧：上传和控制区域 -->
      <el-col :span="12">
        <el-card class="upload-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <!-- 图片模式：多模态标题 -->
              <div v-if="detectionMode === 'image'" class="multimodal-header-left">
                <div class="multimodal-title">
                  <el-icon class="multimodal-icon"><Upload /></el-icon>
                  <span>多模态图像上传</span>
                </div>
                <div class="multimodal-subtitle">上传配对的 RGB 可见光图像与红外 IR 图像</div>
              </div>
              <span v-else>{{ getModeTitle() }}</span>
              <!-- header 右侧操作 -->
              <div class="header-actions">
                <el-button
                  v-if="detectionMode === 'image'"
                  @click="generateExample"
                >
                  <el-icon><Refresh /></el-icon>
                  生成示例
                </el-button>
                <el-button 
                  v-if="detectionMode === 'camera' && !isCameraActive"
                  type="primary" 
                  @click="startCamera" 
                  :loading="$store.state.isLoading"
                >
                  启动摄像头
                </el-button>
                <el-button 
                  v-if="detectionMode === 'camera' && isCameraActive"
                  type="danger" 
                  @click="stopCamera"
                >
                  停止摄像头
                </el-button>
              </div>
            </div>
          </template>
          
          <!-- 图片上传（双模态：RGB + IR） -->
          <div v-if="detectionMode === 'image'" class="upload-section dual-upload-section">
            <el-row :gutter="20">
              <!-- RGB 可见光图像 -->
              <el-col :span="12">
                <div class="upload-label">RGB 可见光图像</div>
                <el-upload
                  class="dual-uploader"
                  :class="{ 'uploader-active': rgbImageUrl }"
                  :show-file-list="false"
                  :auto-upload="false"
                  :on-change="handleRgbChange"
                  accept="image/*"
                  drag
                >
                  <div v-if="!rgbImageUrl" class="dual-upload-placeholder">
                    <div class="dual-upload-icon rgb-icon">
                      <el-icon><Picture /></el-icon>
                    </div>
                    <p class="dual-upload-name">RGB 可见光图像</p>
                    <p class="dual-upload-hint">拖放或点击上传</p>
                    <p class="dual-upload-formats">JPG, PNG, GIF, WEBP</p>
                  </div>
                  <div v-else class="dual-upload-preview">
                    <img :src="rgbImageUrl" class="preview-thumb" alt="RGB图像" />
                    <p class="dual-upload-name">RGB 可见光图像</p>
                    <p class="dual-upload-hint">点击重新上传</p>
                  </div>
                </el-upload>
              </el-col>
              <!-- IR 红外图像 -->
              <el-col :span="12">
                <div class="upload-label">IR 红外图像</div>
                <el-upload
                  class="dual-uploader"
                  :class="{ 'uploader-active': irImageUrl }"
                  :show-file-list="false"
                  :auto-upload="false"
                  :on-change="handleIrChange"
                  accept="image/*"
                  drag
                >
                  <div v-if="!irImageUrl" class="dual-upload-placeholder">
                    <div class="dual-upload-icon ir-icon">
                      <el-icon><Picture /></el-icon>
                    </div>
                    <p class="dual-upload-name">IR 红外图像</p>
                    <p class="dual-upload-hint">拖放或点击上传</p>
                    <p class="dual-upload-formats">JPG, PNG, GIF, WEBP</p>
                  </div>
                  <div v-else class="dual-upload-preview">
                    <img :src="irImageUrl" class="preview-thumb" alt="IR图像" />
                    <p class="dual-upload-name">IR 红外图像</p>
                    <p class="dual-upload-hint">点击重新上传</p>
                  </div>
                </el-upload>
              </el-col>
            </el-row>
          </div>
          
          <!-- 视频上传 -->
          <div v-if="detectionMode === 'video'" class="upload-section">
            <el-upload
              class="video-uploader"
              :action="videoUploadAction"
              :show-file-list="false"
              :before-upload="beforeVideoUpload"
              :on-success="handleVideoSuccess"
              :on-error="handleUploadError"
              :data="{ user_id: $store.getters.currentUser?.id }"
              drag
            >
              <div v-if="!videoUrl" class="upload-placeholder">
                <el-icon class="upload-icon"><VideoPlay /></el-icon>
                <div class="upload-text">
                  <p>拖拽视频到此处，或<em>点击上传</em></p>
                  <p class="upload-tip">支持 MP4、AVI、MOV 格式，大小不超过 100MB</p>
                </div>
              </div>
              <video v-else :src="videoUrl" class="uploaded-video" controls>
                您的浏览器不支持视频播放
              </video>
            </el-upload>
          </div>
          
          <!-- 摄像头 -->
          <div v-if="detectionMode === 'camera'" class="camera-section">
            <div class="camera-container" :class="{ 'camera-overlay-container': isCameraActive }">
              <video 
                ref="cameraVideo" 
                class="camera-video" 
                autoplay 
                muted
                v-show="isCameraActive"
              ></video>
              <canvas 
                ref="cameraCanvas" 
                class="camera-canvas" 
                style="display: none;"
              ></canvas>
              
              <!-- 实时检测框叠加层 -->
              <div v-if="isCameraActive" class="camera-detection-overlay">
                <div 
                  v-for="(detection, index) in realtimeDetections" 
                  :key="`detection-${index}-${detection.confidence}`"
                  class="detection-box"
                  :style="getDetectionBoxStyle(detection)"
                >
                  <span class="detection-label">
                    {{ detection.class }}: {{ (detection.confidence * 100).toFixed(1) }}%
                  </span>
                </div>
              </div>
              
              <div v-if="!isCameraActive" class="camera-placeholder">
                <el-icon class="camera-icon"><Camera /></el-icon>
                <p>点击上方"启动摄像头"开始实时检测</p>
              </div>
            </div>
          </div>
          
          <!-- 检测控制 -->
          <div class="detection-controls" v-if="detectionMode !== 'camera'">
            <el-button 
              type="primary" 
              size="large"
              :disabled="!canDetect"
              :loading="$store.state.isLoading"
              @click="startDetection"
            >
              <el-icon><Search /></el-icon>
              开始检测
            </el-button>
            <el-button @click="resetUpload">
              <el-icon><RefreshRight /></el-icon>
              重新上传
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：检测结果区域 -->
      <el-col :span="12">
        <el-card class="result-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>检测结果</span>
              <div class="result-stats" v-if="detectionResult.detections">
                <el-tag type="success">
                  检测到 {{ detectionResult.detections.length }} 个目标
                </el-tag>
              </div>
            </div>
          </template>
          
          <div class="result-content">
            <!-- 检测结果图片 -->
            <div v-if="detectionResult.result_image && detectionMode === 'image'" class="result-media">
              <img 
                :src="getResultImageUrl()" 
                class="result-image" 
                alt="检测结果" 
                @error="handleImageError"
                @click="openImagePreview(getResultImageUrl())"
              >
              <div class="image-overlay">
                <el-button type="primary" @click="openImagePreview(getResultImageUrl())">
                  <el-icon><ZoomIn /></el-icon>
                  点击放大查看
                </el-button>
              </div>
            </div>
            
            <!-- 检测结果视频 -->
            <div v-if="detectionResult.result_video && detectionMode === 'video'" class="result-media">
              <video 
                :src="getResultVideoUrl()" 
                class="result-video" 
                controls 
                preload="metadata"
                @error="handleVideoError"
                @loadstart="onVideoLoadStart"
                @loadeddata="onVideoLoaded"
              >
                您的浏览器不支持视频播放
              </video>
              <div class="video-overlay">
                <el-button type="primary" @click="openVideoPreview(getResultVideoUrl())">
                  <el-icon><ZoomIn /></el-icon>
                  全屏查看
                </el-button>
              </div>
            </div>
            
            <!-- 检测结果列表 -->
            <div v-if="detectionResult.detections && detectionResult.detections.length > 0" class="detection-list">
              <h4>检测详情</h4>
              <el-table :data="detectionResult.detections" style="width: 100%" size="small" max-height="300">
                <el-table-column prop="class" label="类别" width="120" />
                <el-table-column label="置信度" width="100">
                  <template #default="scope">
                    <el-progress 
                      :percentage="Math.round(scope.row.confidence * 100)" 
                      :stroke-width="8"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="位置">
                  <template #default="scope">
                    <span class="bbox-info">
                      {{ formatBbox(scope.row.bbox) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="帧数" v-if="detectionMode === 'video'" width="80">
                  <template #default="scope">
                    {{ scope.row.frame || '--' }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <!-- 空状态 -->
            <div v-if="!detectionResult.detections && !$store.state.isLoading && detectionMode !== 'camera'" class="empty-result">
              <el-empty description="暂无检测结果">
                <el-button type="primary" @click="startDetection" v-if="canDetect">
                  开始检测
                </el-button>
              </el-empty>
            </div>
            
            <!-- 摄像头模式的空状态 -->
            <div v-if="detectionMode === 'camera' && !isCameraActive && !$store.state.isLoading" class="empty-result">
              <el-empty description="请启动摄像头开始实时检测" />
            </div>
            
            <!-- 实时检测统计 -->
            <div v-if="detectionMode === 'camera' && isCameraActive" class="realtime-stats">
              <el-statistic title="实时检测到的目标" :value="realtimeDetections.length" />
            </div>
            
            <!-- 加载状态 -->
            <div v-if="$store.state.isLoading" class="loading-result">
              <el-loading 
                element-loading-text="正在进行AI检测分析..."
                element-loading-spinner="el-icon-loading"
                element-loading-background="rgba(0, 0, 0, 0.8)"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="showImagePreview"
      title="检测结果 - 放大查看"
      width="90%"
      top="5vh"
      destroy-on-close
      @close="closeImagePreview"
    >
      <div class="preview-container">
        <img 
          v-if="previewImageUrl" 
          :src="previewImageUrl" 
          class="preview-image" 
          alt="检测结果放大图"
          :style="{ 
            transform: `scale(${zoomLevel})`,
            cursor: 'grab'
          }"
          @load="onPreviewImageLoad"
          @error="onPreviewImageError"
          @mousedown="startDrag"
          @mousemove="drag"
          @mouseup="endDrag"
          @wheel="handleWheel"
        >
        <div class="preview-controls">
          <el-button-group>
            <el-button @click="zoomIn">
              <el-icon><ZoomIn /></el-icon>
              放大
            </el-button>
            <el-button @click="zoomOut">
              <el-icon><ZoomOut /></el-icon>
              缩小
            </el-button>
            <el-button @click="resetZoom">
              <el-icon><RefreshRight /></el-icon>
              重置
            </el-button>
            <el-button @click="downloadImage">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
          </el-button-group>
          <div class="zoom-info">
            缩放: {{ Math.round(zoomLevel * 100) }}%
          </div>
        </div>
      </div>
    </el-dialog>
    
    <!-- 视频预览对话框 -->
    <el-dialog
      v-model="showVideoPreview"
      title="检测结果 - 全屏查看"
      width="90%"
      top="5vh"
      destroy-on-close
      @close="closeVideoPreview"
    >
      <div class="preview-container">
        <video 
          v-if="previewVideoUrl" 
          :src="previewVideoUrl" 
          class="preview-video" 
          controls 
          autoplay
        >
          您的浏览器不支持视频播放
        </video>
        <div class="preview-controls">
          <el-button @click="downloadVideo">
            <el-icon><Download /></el-icon>
            下载视频
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { 
  Picture, 
  VideoPlay, 
  Camera, 
  Plus, 
  Search, 
  RefreshRight,
  ZoomIn,
  ZoomOut,
  Download,
  Upload,
  Refresh
} from '@element-plus/icons-vue'

export default {
  name: 'Detection',
  components: {
    Picture,
    VideoPlay,
    Camera,
    Plus,
    Search,
    RefreshRight,
    ZoomIn,
    ZoomOut,
    Download,
    Upload,
    Refresh
  },
  data() {
    return {
      detectionMode: 'image',
      imageUrl: '',
      rgbImageUrl: '',
      irImageUrl: '',
      rgbFile: null,
      irFile: null,
      videoUrl: '',
      isCameraActive: false,
      detectionResult: {},
      realtimeDetections: [],
      cameraStream: null,
      detectionInterval: null,
      uploadAction: '/api/detect_image',
      videoUploadAction: '/api/detect_video',
      videoLoading: false,
      showImagePreview: false,
      showVideoPreview: false,
      previewImageUrl: '',
      previewVideoUrl: '',
      zoomLevel: 1,
      imageWidth: 0,
      imageHeight: 0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0
    }
  },
  computed: {
    canDetect() {
      return (this.detectionMode === 'image' && this.rgbImageUrl && this.irImageUrl) || 
             (this.detectionMode === 'video' && this.videoUrl)
    }
  },
  methods: {
    getModeTitle() {
      const titles = {
        image: '图片上传检测',
        video: '视频上传检测',
        camera: '摄像头实时检测'
      }
      return titles[this.detectionMode]
    },
    
    handleModeChange() {
      // 静默关闭摄像头，不显示提示
      this.silentStopCamera()
      this.resetUpload()
      this.detectionResult = {}
    },
    
    // 图片上传相关
    handleRgbChange(file) {
      const isImage = file.raw.type.startsWith('image/')
      if (!isImage) { ElMessage.error('只能上传图片文件!'); return }
      if (this.rgbImageUrl && this.rgbImageUrl.startsWith('blob:')) URL.revokeObjectURL(this.rgbImageUrl)
      this.rgbFile = file.raw
      this.rgbImageUrl = URL.createObjectURL(file.raw)
    },

    handleIrChange(file) {
      const isImage = file.raw.type.startsWith('image/')
      if (!isImage) { ElMessage.error('只能上传图片文件!'); return }
      if (this.irImageUrl && this.irImageUrl.startsWith('blob:')) URL.revokeObjectURL(this.irImageUrl)
      this.irFile = file.raw
      this.irImageUrl = URL.createObjectURL(file.raw)
    },

    generateExample() {
      ElMessage.info('示例功能暂未实现')
    },

    // 旧单图上传保留（供视频/摄像头模式使用）
    beforeImageUpload(file) {
      const isImage = file.type.startsWith('image/')
      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isImage) { ElMessage.error('只能上传图片文件!'); return false }
      if (!isLt10M) { ElMessage.error('图片大小不能超过 10MB!'); return false }
      this.imageUrl = URL.createObjectURL(file)
      return true
    },
    
    handleImageSuccess(response) {
      if (response.success) {
        this.detectionResult = { ...response }
        ElMessage.success('图片检测完成')
      } else {
        ElMessage.error(response.message)
      }
    },
    
    // 视频上传相关
    beforeVideoUpload(file) {
      const isVideo = file.type.startsWith('video/')
      const isLt100M = file.size / 1024 / 1024 < 100
      
      if (!isVideo) {
        ElMessage.error('只能上传视频文件!')
        return false
      }
      if (!isLt100M) {
        ElMessage.error('视频大小不能超过 100MB!')
        return false
      }
      
      // 保存视频URL用于预览
      this.videoUrl = URL.createObjectURL(file)
      return true
    },
    
    handleVideoSuccess(response) {
      if (response.success) {
        // 确保结果稳定显示
        this.detectionResult = { ...response }
        ElMessage.success(`视频检测完成！处理了 ${response.processed_frames || 0} 帧，检测到 ${response.total_detections || 0} 个目标`)
      } else {
        ElMessage.error(response.message)
      }
    },
    
    handleUploadError(error, file, fileList) {
      console.error('上传错误详情:', error)
      if (error.response) {
        const errorData = error.response.data
        if (errorData && errorData.message) {
          ElMessage.error(`上传失败: ${errorData.message}`)
        } else {
          ElMessage.error(`上传失败: HTTP ${error.response.status}`)
        }
      } else {
        ElMessage.error('上传失败: ' + error.message)
      }
    },
    
    // 视频加载事件
    onVideoLoadStart() {
      this.videoLoading = true
      console.log('视频开始加载...')
    },
    
    onVideoLoaded() {
      this.videoLoading = false
      console.log('视频加载完成')
    },
    
    handleImageError(event) {
      console.error('图片加载错误:', event)
      ElMessage.error('图片加载失败，请检查网络连接')
    },
    
    handleVideoError(event) {
      console.error('视频加载错误:', event)
      const video = event.target
      let errorMessage = '视频加载失败'
      
      if (video.error) {
        switch (video.error.code) {
          case 1: // MEDIA_ERR_ABORTED
            errorMessage = '视频加载被中止'
            break
          case 2: // MEDIA_ERR_NETWORK
            errorMessage = '视频网络加载错误'
            break
          case 3: // MEDIA_ERR_DECODE
            errorMessage = '视频解码错误，格式可能不支持'
            break
          case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
            errorMessage = '视频格式不支持或文件损坏'
            break
          default:
            errorMessage = '视频播放出现未知错误'
        }
      }
      
      ElMessage.error(errorMessage)
      
      // 提供解决建议
      this.$notify({
        title: '视频加载失败',
        message: '建议：1. 检查网络连接 2. 尝试其他视频格式 3. 重新上传视频',
        type: 'warning',
        duration: 8000
      })
    },
    
    // 摄像头相关
    async startCamera() {
      try {
        this.cameraStream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
          } 
        })
        
        if (this.$refs.cameraVideo) {
          this.$refs.cameraVideo.srcObject = this.cameraStream
          this.isCameraActive = true
          
          // 等待视频加载后开始检测
          this.$refs.cameraVideo.onloadedmetadata = () => {
            this.startRealtimeDetection()
          }
          
          ElMessage.success('摄像头已启动')
        }
      } catch (error) {
        ElMessage.error('无法访问摄像头: ' + error.message)
      }
    },
    
    stopCamera() {
      this.silentStopCamera()
      ElMessage.success('摄像头已关闭')
    },
    
    silentStopCamera() {
      if (this.cameraStream) {
        this.cameraStream.getTracks().forEach(track => track.stop())
        this.cameraStream = null
      }
      if (this.detectionInterval) {
        clearInterval(this.detectionInterval)
        this.detectionInterval = null
      }
      this.isCameraActive = false
      this.realtimeDetections = []
    },
    
    startRealtimeDetection() {
      if (this.detectionInterval) {
        clearInterval(this.detectionInterval)
      }
      
      this.detectionInterval = setInterval(async () => {
        if (this.isCameraActive && this.$refs.cameraVideo && this.$refs.cameraVideo.readyState === 4) {
          const canvas = this.$refs.cameraCanvas
          const video = this.$refs.cameraVideo
          const ctx = canvas.getContext('2d')
          
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          
          if (canvas.width > 0 && canvas.height > 0) {
            ctx.drawImage(video, 0, 0)
            const imageData = canvas.toDataURL('image/jpeg', 0.8)
            
            try {
              const result = await this.$store.dispatch('processFrame', imageData)
              if (result.success) {
                // 使用Vue的响应式更新，避免闪烁
                this.$nextTick(() => {
                  this.realtimeDetections = [...result.detections]
                })
              }
            } catch (error) {
              console.error('实时检测失败:', error)
            }
          }
        }
      }, 1000) // 降低检测频率到1秒，减少闪烁
    },
    
    // 检测相关
    async startDetection() {
      if (this.detectionMode === 'image') {
        if (!this.rgbFile || !this.irFile) {
          ElMessage.warning('请先上传 RGB 和 IR 两张图片')
          return
        }
        const formData = new FormData()
        formData.append('rgb_image', this.rgbFile)
        formData.append('ir_image', this.irFile)
        if (this.$store.getters.currentUser?.id) {
          formData.append('user_id', this.$store.getters.currentUser.id)
        }
        this.$store.commit('setLoading', true)
        try {
          const response = await fetch('/api/detect_image', {
            method: 'POST',
            body: formData
          })
          const result = await response.json()
          if (result.success) {
            this.detectionResult = { ...result }
            ElMessage.success('图片检测完成')
          } else {
            ElMessage.error(result.message || '检测失败')
          }
        } catch (error) {
          ElMessage.error('检测请求失败: ' + error.message)
        } finally {
          this.$store.commit('setLoading', false)
        }
      } else if (this.detectionMode === 'video' && this.videoUrl) {
        ElMessage.info('请重新上传视频以触发检测')
      }
    },
    
    resetUpload() {
      // 清理旧的 URL
      if (this.imageUrl && this.imageUrl.startsWith('blob:')) URL.revokeObjectURL(this.imageUrl)
      if (this.rgbImageUrl && this.rgbImageUrl.startsWith('blob:')) URL.revokeObjectURL(this.rgbImageUrl)
      if (this.irImageUrl && this.irImageUrl.startsWith('blob:')) URL.revokeObjectURL(this.irImageUrl)
      if (this.videoUrl && this.videoUrl.startsWith('blob:')) URL.revokeObjectURL(this.videoUrl)
      
      this.imageUrl = ''
      this.rgbImageUrl = ''
      this.irImageUrl = ''
      this.rgbFile = null
      this.irFile = null
      this.videoUrl = ''
      this.detectionResult = {}
    },
    
    resetAll() {
      this.resetUpload()
      this.silentStopCamera()
    },
    
    // 结果显示相关
    getResultImageUrl() {
      return this.detectionResult.result_image
    },
    
    getResultVideoUrl() {
      return this.detectionResult.result_video
    },
    
    formatBbox(bbox) {
      if (!bbox || bbox.length !== 4) return ''
      return `(${Math.round(bbox[0])}, ${Math.round(bbox[1])}) - (${Math.round(bbox[2])}, ${Math.round(bbox[3])})`
    },
    
    getDetectionBoxStyle(detection) {
      if (!detection.bbox || !this.$refs.cameraVideo) return {}
      
      const video = this.$refs.cameraVideo
      const container = video.parentElement
      const videoRect = video.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()
      
      const [x1, y1, x2, y2] = detection.bbox
      
      // 计算缩放比例
      const scaleX = videoRect.width / video.videoWidth
      const scaleY = videoRect.height / video.videoHeight
      
      // 计算相对于容器的位置
      const left = (videoRect.left - containerRect.left) + (x1 * scaleX)
      const top = (videoRect.top - containerRect.top) + (y1 * scaleY)
      const width = (x2 - x1) * scaleX
      const height = (y2 - y1) * scaleY
      
      return {
        position: 'absolute',
        left: `${left}px`,
        top: `${top}px`,
        width: `${width}px`,
        height: `${height}px`,
        border: '2px solid #00ff00',
        backgroundColor: 'rgba(0, 255, 0, 0.1)',
        pointerEvents: 'none',
        zIndex: 10
      }
    },
    
    openImagePreview(imageUrl) {
      this.previewImageUrl = imageUrl
      this.showImagePreview = true
    },
    
    openVideoPreview(videoUrl) {
      this.previewVideoUrl = videoUrl
      this.showVideoPreview = true
    },
    
    closeImagePreview() {
      this.showImagePreview = false
      this.previewImageUrl = ''
    },
    
    closeVideoPreview() {
      this.showVideoPreview = false
      this.previewVideoUrl = ''
    },
    
    onPreviewImageLoad() {
      const image = new Image()
      image.src = this.previewImageUrl
      image.onload = () => {
        this.imageWidth = image.width
        this.imageHeight = image.height
      }
    },
    
    onPreviewImageError(event) {
      console.error('图片加载错误:', event)
      ElMessage.error('图片加载失败，请检查网络连接')
    },
    
    zoomIn() {
      this.zoomLevel += 0.1
      if (this.zoomLevel > 3) this.zoomLevel = 3
    },
    
    zoomOut() {
      this.zoomLevel -= 0.1
      if (this.zoomLevel < 0.1) this.zoomLevel = 0.1
    },
    
    resetZoom() {
      this.zoomLevel = 1
    },
    
    handleWheel(event) {
      event.preventDefault()
      const delta = event.deltaY > 0 ? -0.05 : 0.05
      this.zoomLevel += delta
      if (this.zoomLevel > 3) this.zoomLevel = 3
      if (this.zoomLevel < 0.1) this.zoomLevel = 0.1
    },
    
    startDrag(event) {
      this.isDragging = true
      this.dragStartX = event.clientX
      this.dragStartY = event.clientY
    },
    
    drag(event) {
      if (!this.isDragging) return
      // 这里可以实现图片拖拽移动功能
    },
    
    endDrag() {
      this.isDragging = false
    },
    
    downloadImage() {
      if (!this.previewImageUrl) return
      
      const link = document.createElement('a')
      link.href = this.previewImageUrl
      link.download = `检测结果_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.jpg`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      ElMessage.success('图片下载已开始')
    },
    
    downloadVideo() {
      if (!this.previewVideoUrl) return
      
      const link = document.createElement('a')
      link.href = this.previewVideoUrl
      link.download = `检测结果_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      ElMessage.success('视频下载已开始')
    }
  },
  
  beforeUnmount() {
    this.silentStopCamera()
    this.resetUpload()
  }
}
</script>

<style scoped>
.detection-container {
  max-width: 1400px;
  margin: 0 auto;
}

.mode-selector {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.result-stats {
  display: flex;
  gap: 10px;
}

.upload-card, .result-card {
  min-height: 600px;
}

/* 多模态 header */
.multimodal-header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.multimodal-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.multimodal-icon {
  color: #409eff;
  font-size: 18px;
}

.multimodal-subtitle {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 双图上传 */
.dual-upload-section {
  margin-bottom: 20px;
}

.upload-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.dual-uploader {
  width: 100%;
}

.dual-uploader :deep(.el-upload) {
  width: 100%;
}

.dual-uploader :deep(.el-upload-dragger) {
  width: 100%;
  height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #d9d9d9;
  border-radius: 10px;
  background: #fafafa;
  transition: border-color 0.2s, background 0.2s;
}

.dual-uploader :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #f0f7ff;
}

.uploader-active :deep(.el-upload-dragger) {
  border-color: #67c23a;
  background: #f0faf0;
}

.dual-upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.dual-upload-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  margin-bottom: 4px;
}

.rgb-icon {
  background: linear-gradient(135deg, #c845e8, #e86845);
  color: #fff;
}

.ir-icon {
  background: linear-gradient(135deg, #e85c45, #e8a045);
  color: #fff;
}

.dual-upload-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.dual-upload-hint {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.dual-upload-formats {
  font-size: 11px;
  color: #c0c4cc;
  background: #f5f7fa;
  padding: 2px 10px;
  border-radius: 4px;
  margin: 0;
}

.dual-upload-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px;
}

.preview-thumb {
  max-width: 100%;
  max-height: 150px;
  border-radius: 6px;
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

.upload-section {
  margin-bottom: 20px;
}

.image-uploader, .video-uploader {
  width: 100%;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 20px;
}

.upload-text {
  text-align: center;
}

.upload-text p {
  margin: 5px 0;
}

.upload-tip {
  color: #999;
  font-size: 12px;
}

.uploaded-image, .uploaded-video {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
}

.camera-section {
  margin-bottom: 20px;
}

.camera-container {
  position: relative;
  width: 100%;
  height: 300px;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.camera-overlay-container {
  border-color: #409eff;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.camera-canvas {
  position: absolute;
  top: 0;
  left: 0;
  visibility: hidden;
}

.camera-placeholder {
  text-align: center;
  color: #999;
}

.camera-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.camera-detection-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.detection-box {
  position: absolute;
  border: 2px solid #00ff00;
  background: rgba(0, 255, 0, 0.1);
  pointer-events: none;
}

.detection-label {
  position: absolute;
  top: -25px;
  left: 0;
  background: #00ff00;
  color: black;
  padding: 2px 6px;
  font-size: 12px;
  border-radius: 3px;
  white-space: nowrap;
  pointer-events: none;
}

.detection-controls {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.result-content {
  position: relative;
  min-height: 400px;
}

.result-media {
  margin-bottom: 20px;
  text-align: center;
  position: relative;
}

.result-image, .result-video {
  max-width: 100%;
  max-height: 350px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.3s ease;
}

.result-image:hover, .result-video:hover {
  transform: scale(1.02);
}

.image-overlay, .video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: 8px;
}

.result-media:hover .image-overlay,
.result-media:hover .video-overlay {
  opacity: 1;
}

.detection-list {
  margin-top: 20px;
}

.detection-list h4 {
  margin-bottom: 15px;
  color: #333;
}

.bbox-info {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.empty-result {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.realtime-stats {
  text-align: center;
  margin-top: 20px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
}

.loading-result {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-container {
  position: relative;
  width: 100%;
  height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.1s ease;
  user-select: none;
}

.preview-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.preview-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  padding: 10px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  backdrop-filter: blur(10px);
}

.preview-controls .el-button {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.preview-controls .el-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.zoom-info {
  color: white;
  font-size: 12px;
  text-align: center;
  margin-top: 5px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

:deep(.el-radio-button__inner) {
  padding: 12px 20px;
}
</style> 