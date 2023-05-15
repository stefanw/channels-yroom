import "prosemirror-example-setup/style/style.css"
import "prosemirror-gapcursor/style/gapcursor.css"
import "prosemirror-menu/style/menu.css"
import "prosemirror-view/style/prosemirror.css"
import './style.css'

import { startEditor } from './prosemirror.js'
import { startTipTapEditor } from './tiptap.js'

const roomSettings = JSON.parse(document.getElementById('room-settings').textContent);


window.addEventListener('load', () => {
  const wsURL = 'ws://'
  + window.location.host + roomSettings.wsPath

  if (roomSettings.editor === "prosemirror") {
    startEditor(wsURL, roomSettings.roomName)
  } else if (roomSettings.editor === "tiptap") {
    const element = document.querySelector('#editor-container')
    let wsTipTapUrl = wsURL + roomSettings.roomName
    startTipTapEditor(element, wsTipTapUrl, roomSettings.roomName)
  }
})