import { HocuspocusProvider } from '@hocuspocus/provider';
import { Editor } from '@tiptap/core';
import Collaboration from '@tiptap/extension-collaboration';
import CollaborationCursor from '@tiptap/extension-collaboration-cursor';
import StarterKit from '@tiptap/starter-kit';
import * as Y from 'yjs';

function getRandomColor() {
    const colors = [
        '#ff0000',
        '#00ff00',
        '#0000ff',
        '#ffff00',
        '#00ffff',
        '#ff00ff',
        '#000000',
        '#ffffff',
    ]
    return colors[Math.floor(Math.random() * colors.length)]
}

function getRandomName () {
    return "User "+ Math.random()
}


export function startTipTapEditor(element, wsURL, roomName) {
    const ydoc = new Y.Doc()
    const provider = new HocuspocusProvider({
        url: wsURL,
        name: roomName,
        document: ydoc,
        // onSynced(data) {
        //     console.log(data)
        // },
    });
    // provider.on('connect', () => {
    //   provider.forceSync()
    // })

    const editor = new Editor({
        element, 
        extensions: [
            StarterKit.configure({
                history: false,
            }),
            Collaboration.configure({
                document: ydoc,
                field: 'content',
            }),
            CollaborationCursor.configure({
                provider: provider,
                user: { name: getRandomName(), color: getRandomColor() },
            }),
        ],
    })
}