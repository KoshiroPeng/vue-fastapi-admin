import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),
  // WiFi operations
  getWifiHealth: () => request.get('/dashboard/health'),
  getWifiStatistics: (params = {}) => request.get('/dashboard/statistics', { params }),
  getWifiRuntimeConfig: () => request.get('/runtime-config/summary'),
  getWifiOnlineUsers: (params = {}) => request.get('/dashboard/online-users', { params }),
  getWifiRadiusLogs: (data = {}) => request.post('/dashboard/radius-logs', data),
  // Passenger Portal
  verifyBoardingPass: (data = {}) =>
    request.post('/portal/boarding-pass/verify', data, { noNeedToken: true }),
  verifyPassport: (file, context = {}) =>
    request.post('/portal/passport/verify', file, {
      noNeedToken: true,
      headers: {
        'Content-Type': file.type,
        'X-Client-IP': context.clientIp,
        'X-Client-MAC': context.clientMac,
        'X-SSID': context.ssid,
        'X-Device-MAC': context.deviceMac,
        'X-Device-ESN': context.deviceEsn,
        'X-AP-MAC': context.apMac,
        'X-Node-IP': context.nodeIp,
      },
    }),
  startWechatAuth: (data = {}) =>
    request.post('/portal/wechat/auth/start', data, { noNeedToken: true }),
  mockCompleteWechatAuth: (authTxId) =>
    request.post('/portal/wechat/auth/mock-complete', null, {
      params: { auth_tx_id: authTxId },
      noNeedToken: true,
    }),
  getWechatAuthStatus: (authTxId) =>
    request.get('/portal/wechat/auth/status', {
      params: { auth_tx_id: authTxId },
      noNeedToken: true,
    }),
}
