export interface SlideNavigateData {
    type: 'slide.navigate'
    slideNbr: number
    clicks?: number
}

export interface SlideNextData {
    type: 'slide.next'
}

export interface SlidePrevData {
    type: 'slide.prev'
}

export type SlideMessageData = SlideNavigateData | SlideNextData | SlidePrevData
export interface SlideMessage {
    appId: 'slidev'
    data: SlideMessageData
}
