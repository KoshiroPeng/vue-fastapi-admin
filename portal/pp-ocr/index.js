const PR = (function () {
  let userName = 'test'
  let baseUrl = 'http://172.16.4.179:8888'
  const PR = function (params) {
    if (!params) {
      return false
    }
    if (params.userName) {
      userName = params.userName
    }
    if (params.baseUrl) {
      baseUrl = params.baseUrl
    }
  }
  PR.prototype.init = function () {

  }
  // 获取护照信息
  PR.prototype.getPassportInfo = function (callback, isCamera, showLoaing) {
    const dom = document.createElement('input')
    dom.type = 'file'
    dom.accept = 'image/*'
    // 直接拍照
    if (isCamera) {
      dom.capture = 'camera'
    }
    dom.style.display = 'none'
    dom.style.zIndex = -1
    document.body.appendChild(dom);
    dom.onchange = (e) => {
      getChanges(e, callback, showLoaing)
      document.body.removeChild(dom)
    }
    dom.click()
  }
  // 格式化返回的数据
  function formatData(data) {
    const _d = {}
    data.forEach(item => {
      if (item.desc == '护照类型') {
        _d.passportType = item.content || ''
      } else if (item.desc == '护照号码MRZ') {
        _d.passportNumberMRZ = item.content || ''
      } else if (item.desc == '本国姓名') {
        _d.nativeName = item.content || ''
      } else if (item.desc == '英文姓名') {
        _d.nameInEnglish = item.content || ''
      } else if (item.desc == '性别') {
        _d.sex = item.content || ''
      } else if (item.desc == '出生日期') {
        _d.birthDate = item.content || ''
      } else if (item.desc == '有效期至') {
        _d.expireDate = item.content || ''
      } else if (item.desc == '签发国代码') {
        _d.issuedCode = item.content || ''
      } else if (item.desc == '英文姓') {
        _d.englishSurname = item.content || ''
      } else if (item.desc == '英文名') {
        _d.englishName = item.content || ''
      } else if (item.desc == 'MRZ1') {
        _d.MRZ1 = item.content || ''
      } else if (item.desc == 'MRZ2') {
        _d.MRZ2 = item.content || ''
      } else if (item.desc == '持证人国籍代码') {
        _d.countryCode = item.content || ''
      } else if (item.desc == '护照号码') {
        _d.passportNumber = item.content || ''
      } else if (item.desc == '签发地点') {
        _d.issuePlace = item.content || ''
      } else if (item.desc == '签发日期') {
        _d.issueDate = item.content || ''
      } else if (item.desc == 'OCR MRZ') {
        _d.MRZ = item.content || ''
      } else if (item.desc == '签发日期') {
        _d.issueDate = item.content || ''
      }
    })
    return _d
  }
  function getChanges(e, callback, showLoaing) {
    const files = e.target.files
    const d = new FormData()
    d.append('username', userName)
    d.append('file', files[0])
    d.append('typeId', '13')
    // 上传
    showLoaing(true)
    uploadAjax({
      url: baseUrl + '/cxfServerX/doAllCardFileRecon',
      formData: d
    }, (res) => {
      showLoaing(false)
      const result = typeof res === 'string' ? JSON.parse(res) : res
      const _d = result.data && result.data.cardsinfo && result.data.cardsinfo.card && result.data.cardsinfo.card
      if (_d && _d.type === 13) {
        callback && callback({
          status: '200',
          msg: '识别成功',
          data: formatData(_d.item || [])
        })
      } else {
        let _msg = result.data && result.data.message && result.message.value
        if (result.data && result.data.message && result.data.message.status == 13) {
          _msg = '识别错误, 请重试!'
        }
        callback && callback({
          status: '400',
          msg: _msg,
          data: result.data && result.data.message
        })
      }
    }, (er) => {
      showLoaing(false)
      callback && callback({
        status: '500',
        msg: '服务连接错误, 请稍后重试!'
      })
    })
    e.target.value = ''
  }

  // 请求封装
  function uploadAjax(params, onSuccess, onError) {
    let xhr = new XMLHttpRequest();
    xhr.open('POST', params.url, true);
    
    xhr.onload = function() {
      if (xhr.status >= 200 && xhr.status < 400) {
        onSuccess(xhr.responseText);
      } else {
        onError(xhr.responseText);
      }
    };
    xhr.onerror = function() {
      onError(xhr.responseText);
    };
    xhr.send(params.formData);
  }
  return PR
})()