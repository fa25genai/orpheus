export interface SlideMessage {
    appId: 'slidev'
    data: SlideMessageData
}

export interface SlideMessageData {
    type: 'slide.navigate' | 'slide.next' | 'slide.prev'
    value?: number
}
