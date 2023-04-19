import { exampleSetup } from 'prosemirror-example-setup'
import { keymap } from 'prosemirror-keymap'
import { EditorState } from 'prosemirror-state'
import { EditorView } from 'prosemirror-view'
import { redo, undo, yCursorPlugin, ySyncPlugin, yUndoPlugin } from 'y-prosemirror'
import { WebsocketProvider } from 'y-websocket'
import * as Y from 'yjs'
import { schema } from './schema.js'


export function startEditor(wsURL, roomName) {
    const ydoc = new Y.Doc()
    const provider = new WebsocketProvider(wsURL, roomName, ydoc)
    const yXmlFragment = ydoc.getXmlFragment('prosemirror')

    const editor = document.createElement('div')
    editor.setAttribute('id', 'editor')
    const editorContainer = document.createElement('div')
    editorContainer.insertBefore(editor, null)
    const prosemirrorView = new EditorView(editor, {
        state: EditorState.create({
            schema,
            plugins: [
                ySyncPlugin(yXmlFragment),
                yCursorPlugin(provider.awareness),
                yUndoPlugin(),
                keymap({
                    'Mod-z': undo,
                    'Mod-y': redo,
                    'Mod-Shift-z': redo
                })
            ].concat(exampleSetup({ schema }))
        })
    })
    document.body.insertBefore(editorContainer, null)

    // @ts-ignore
    window.example = { provider, ydoc, yXmlFragment, prosemirrorView }
}