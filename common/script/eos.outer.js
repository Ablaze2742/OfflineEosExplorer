/* Milovana.com Resource File - Copyright 2006-2022 Milovana.com */
jQuery(function () {
  var iframe = document.getElementsByClassName('eosIframe')[0]
  var script
  var rpcMethods = {
    load: function (params) {
      var searchParams = new URLSearchParams(window.location.search)
      var teaseId = Number(document.body.getAttribute('data-tease-id'))
      var title = document.body.getAttribute('data-title')
      var author = document.body.getAttribute('data-author')
      var preview = document.body.getAttribute('data-preview') === 'true' || searchParams.has('preview')
      var key = document.body.getAttribute('data-key')
      var link = document.querySelector("link[rel~='icon']");
      if (!link) {
          link = document.createElement('link');
          link.rel = 'icon';
          document.head.appendChild(link);
      }
      link.href = './icon.png?' + Date.now();
      return fetch('./config.ini?' + Date.now()).then(x => x.text()).then(y => {
        var config = parseINIString(y)
        title = config.title
        author = config.author
        document.title = title
        preview = preview || config.preview === 'true'
        return fetch('eosscript.json?_dt='+Date.now()+'&id=' + teaseId + (preview ? '&preview=1' : '') + (key ? '&key=' + key : ''), { credentials: 'same-origin' }).then(function (res) { return res.json() }).then(function (json) {
          script = json
          return { title: title, author: author, script: script, preview: preview }
        })
      })
    }, queryMedia: function (params) {
      var authorId = Number(document.body.getAttribute('data-author-id'))
      var teaseId = Number(document.body.getAttribute('data-tease-id'))
      var locator = params.locator
      var size = params.size
      var type = params.type
      var wildcard = locator.indexOf('*') !== -1
      return fetch('/media/query.php' + '?url=' + encodeURIComponent(locator) + '&size=' + encodeURIComponent(size) + '&type=' + encodeURIComponent(type) + '&context=timg://' + authorId + '/' + teaseId + '/' + (wildcard ? '&random=' + Math.random() : '')).then(function (res) { return res.json() })
    }, goToAuthor: function () {
      var authorId = Number(document.body.getAttribute('data-author-id'))
      /*window.location.href='/webteases/?author='+authorId*/
      return !0
    }, loadStorage: function () {
      var teaseId = Number(document.body.getAttribute('data-tease-id'))
      var isLoggedIn = document.body.getAttribute('data-is-logged-in') === 'true'
      if (!script) { throw new Error('script has not been loaded yet') }
      if (!script.modules || !script.modules.storage) { throw new Error('storage module is not enabled for this script') }
      if (isLoggedIn) {
        return Promise.resolve(jQuery.ajax({
          type: 'POST', url: '/graphql/', contentType: 'application/json', data: JSON.stringify({
            query: `query ($teaseId: ID!) {
              loadTeaseStorage(teaseId: $teaseId) {
                data
              }
            }`, variables: { teaseId: teaseId }
          })
        })).then(function (response) { return response.data.loadTeaseStorage.data })
      } else { return localStorage['teaseStorage_' + teaseId] || '{}' }
    }, saveStorage: function (params) {
      var teaseId = Number(document.body.getAttribute('data-tease-id'))
      var isLoggedIn = document.body.getAttribute('data-is-logged-in') === 'true'
      if (!script) { throw new Error('script has not been loaded yet') }
      if (!script.modules || !script.modules.storage) { throw new Error('storage module is not enabled for this script') }
      if (isLoggedIn) {
        return Promise.resolve(jQuery.ajax({
          type: 'POST', url: '/graphql/', contentType: 'application/json', data: JSON.stringify({
            query: `mutation ($teaseId: ID!, $data: String!) {
              saveTeaseStorage(teaseId: $teaseId, data: $data)
            }`, variables: { teaseId: teaseId, data: params.state }
          })
        })).then(function () { return !0 })
      } else {
        localStorage['teaseStorage_' + teaseId] = params.state
        return !0
      }
    }, openRatingDialog: function () {
      var dialog = document.getElementById('eosRatingDialog')
      var isLoggedIn = document.body.getAttribute('data-is-logged-in') === 'true'
      dialog.style.display = 'flex'
      var messageEl = document.querySelector('.eosRatingDialog .message')
      messageEl.innerHTML = 'Thanks for playing!<br><br>'
      +'<div style="font-size: 80%">You can '
      +'<a style="color:white" href="#" onclick="window.location.reload()">reload</a> if you want.</div>'
      /*
      if (!isLoggedIn) {
        var messageEl = document.querySelector('.eosRatingDialog .message')
        messageEl.innerHTML = 'In order to rate this tease, you need to be logged in first.'
      }
      */
      return !0
    }
  }
  window.addEventListener('message', function (event) {
    if (event.source !== iframe.contentWindow) {
      console.error('Received message from unknown source, ignoring')
      return
    }
    var method = event.data.method
    var params = event.data.params
    var id = event.data.id
    if (Object.keys(rpcMethods).indexOf(method) === -1) {
      console.error('Unknown rpc method "' + method + '"')
      return
    }
    Promise.resolve(rpcMethods[method](params)).then(function (result) { iframe.contentWindow.postMessage({ jsonrpc: '2.0', result: result, id: id }, '*') }).catch(function (error) { iframe.contentWindow.postMessage({ jsonrpc: '2.0', error: { message: error.message }, id: id }, '*') })
  })
  document.querySelector('.eosRatingDialog').addEventListener('click', function (e) {
    if (e.currentTarget !== e.target) { return }
    document.querySelector('.eosRatingDialog').style.display = 'none'
  })
  document.querySelector('.eosRatingDialog .close').addEventListener('click', function () { document.querySelector('.eosRatingDialog').style.display = 'none' })
  var teaseId = Number(document.body.getAttribute('data-tease-id'))
  var starButtons = document.querySelectorAll('.eosRatingDialog .star.rating')
  for (var i = 0; i < starButtons.length; i++) {
    starButtons[i].addEventListener('click', function (e) {
      var rating = e.currentTarget.dataset.rating
      var starsEl = document.querySelector('.eosRatingDialog .stars')
      starsEl.style.display = 'none'
      var messageEl = document.querySelector('.eosRatingDialog .message')
      messageEl.innerHTML = 'Loading...'
      fetch('/graphql/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: 'mutation { rateTease(teaseId: ' + teaseId + ', rating: ' + rating + ') { id } }' }) }).then(function (res) { return res.json() }).then(function (json) { if (json.data) { messageEl.innerHTML = 'Thanks for submitting your rating!' } else { messageEl.innerHTML = 'Sorry, an error occurred. Please try again later.' } })
    })
  }
  function parseINIString(data){
    var regex = {
        section: /^\s*\[\s*([^\]]*)\s*\]\s*$/,
        param: /^\s*([^=]+?)\s*=\s*(.*?)\s*$/,
        comment: /^\s*;.*$/
    };
    var value = {};
    var lines = data.split(/[\r\n]+/);
    var section = null;
    lines.forEach(function(line){
        if(regex.comment.test(line)){
            return;
        }else if(regex.param.test(line)){
            var match = line.match(regex.param);
            if(section){
                value[section][match[1]] = match[2];
            }else{
                value[match[1]] = match[2];
            }
        }else if(regex.section.test(line)){
            var match = line.match(regex.section);
            value[match[1]] = {};
            section = match[1];
        }else if(line.length == 0 && section){
            section = null;
        };
    });
    return value;
  }
})