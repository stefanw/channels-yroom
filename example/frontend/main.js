import './style.css'
import "prosemirror-view/style/prosemirror.css"
import "prosemirror-example-setup/style/style.css"
import "prosemirror-menu/style/menu.css"
import "prosemirror-gapcursor/style/gapcursor.css"

import { startEditor } from './prosemirror.js';

const roomName = JSON.parse(document.getElementById('room-name').textContent);

const wsURL = 'ws://'
  + window.location.host
  + '/ws/textcollab/'


window.addEventListener('load', () => {
  startEditor(wsURL, roomName)
})