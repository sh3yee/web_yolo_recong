import { createStore } from 'vuex'
import axios from 'axios'

// 临时硬编码IP地址进行测试
// 请将下面的IP地址替换为您的实际服务器IP地址
const API_BASE_URL = 'http://192.168.1.100:5000/api'  // 请修改这个IP地址

// 调试信息
console.log('API_BASE_URL:', API_BASE_URL)
console.log('环境变量:', process.env.VUE_APP_API_BASE_URL)

export default createStore({
  state: {
    user: null,
    isLoading: false,
    detectionResults: [],
    history: []
  },
  getters: {
    isAuthenticated: state => !!state.user,
    currentUser: state => state.user
  },
  mutations: {
    SET_USER(state, user) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    },
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    SET_DETECTION_RESULTS(state, results) {
      state.detectionResults = results
    },
    SET_HISTORY(state, history) {
      state.history = history
    }
  },
  actions: {
    async login({ commit }, credentials) {
      try {
        commit('SET_LOADING', true)
        console.log('发送登录请求到:', `${API_BASE_URL}/login`)
        const response = await axios.post(`${API_BASE_URL}/login`, credentials)
        if (response.data.success) {
          commit('SET_USER', response.data.user)
          return { success: true, message: response.data.message }
        } else {
          return { success: false, message: response.data.message }
        }
      } catch (error) {
        console.error('登录错误:', error)
        return {
          success: false,
          message: error.response?.data?.message || '登录失败'
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async register({ commit }, credentials) {
      try {
        commit('SET_LOADING', true)
        const response = await axios.post(`${API_BASE_URL}/register`, credentials)
        return {
          success: response.data.success,
          message: response.data.message
        }
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '注册失败'
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    logout({ commit }) {
      commit('SET_USER', null)
    },
    async detectImage({ commit, state }, formData) {
      try {
        commit('SET_LOADING', true)
        formData.append('user_id', state.user.id)
        const response = await axios.post(`${API_BASE_URL}/detect_image`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        if (response.data.success) {
          commit('SET_DETECTION_RESULTS', response.data)
        }
        return response.data
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '图片检测失败'
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async detectVideo({ commit, state }, formData) {
      try {
        commit('SET_LOADING', true)
        formData.append('user_id', state.user.id)
        const response = await axios.post(`${API_BASE_URL}/detect_video`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        if (response.data.success) {
          commit('SET_DETECTION_RESULTS', response.data)
        }
        return response.data
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '视频检测失败'
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async processFrame({ state }, imageData) {
      try {
        const response = await axios.post(`${API_BASE_URL}/process_frame`, {
          image: imageData,
          user_id: state.user.id
        })
        return response.data
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '帧处理失败'
        }
      }
    },
    async fetchHistory({ commit, state }) {
      try {
        const response = await axios.get(`${API_BASE_URL}/history/${state.user.id}`)
        if (response.data.success) {
          commit('SET_HISTORY', response.data.history)
        }
        return response.data
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '获取历史记录失败'
        }
      }
    },
    initializeAuth({ commit }) {
      const user = localStorage.getItem('user')
      if (user) {
        commit('SET_USER', JSON.parse(user))
      }
    }
  }
})