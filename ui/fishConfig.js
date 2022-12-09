export const BACKGROUND = 'background'
export const OCTO = "octo"
export const PUFFY = "puffy"
export const PUFFY_HIGH_RESOLUTION = `${PUFFY}0`
export const PUFFY_MEDIUM_RESOLUTION = `${PUFFY}1`
export const PUFFY_LOW_RESOLUTION = `${PUFFY}2`
export const OCTO_HIGH_RESOLUTION = `${OCTO}0`
export const OCTO_MEDIUM_RESOLUTION = `${OCTO}1`
export const OCTO_LOW_RESOLUTION = `${OCTO}2`
export const DEAD = "DEAD"
export const DEAD_PUFFY = `${DEAD}${PUFFY}`
export const DEAD_OCTO = `${DEAD}${OCTO}`
export const DEAD_PUFFY_HIGH_RESOLUTION = `${DEAD}${PUFFY}0`
export const DEAD_PUFFY_MEDIUM_RESOLUTION = `${DEAD}${PUFFY}1`
export const DEAD_PUFFY_LOW_RESOLUTION = `${DEAD}${PUFFY}2`
export const DEAD_OCTO_HIGH_RESOLUTION = `${DEAD}${OCTO}0`
export const DEAD_OCTO_MEDIUM_RESOLUTION = `${DEAD}${OCTO}1`
export const DEAD_OCTO_LOW_RESOLUTION = `${DEAD}${OCTO}2`

export const FISH_IMAGE_MAP = {
  [BACKGROUND]: './assets/images/background.png',
  [PUFFY_HIGH_RESOLUTION]: "./assets/images/puffy.png",
  [PUFFY_MEDIUM_RESOLUTION]: "./assets/images/puffy1.png",
  [PUFFY_LOW_RESOLUTION]: "./assets/images/puffy2.png",

  [OCTO_HIGH_RESOLUTION]: "./assets/images/octo.png",
  [OCTO_MEDIUM_RESOLUTION]: "./assets/images/octo1.png",
  [OCTO_LOW_RESOLUTION]: "./assets/images/octo2.png",

  [DEAD_PUFFY_HIGH_RESOLUTION]: "./assets/images/puffysick.png",
  [DEAD_PUFFY_MEDIUM_RESOLUTION]: "./assets/images/puffysick1.png",
  [DEAD_PUFFY_LOW_RESOLUTION]: "./assets/images/puffysick2.png",

  [DEAD_OCTO_HIGH_RESOLUTION]: "./assets/images/octosick.png",
  [DEAD_OCTO_MEDIUM_RESOLUTION]: "./assets/images/octosick1.png",
  [DEAD_OCTO_LOW_RESOLUTION]: "./assets/images/octosick2.png",
}

export const FISH_IMAGE_SIZE = {
  [BACKGROUND]: {w: 70, h: 70},
  [OCTO_HIGH_RESOLUTION]: {w: 122, h: 70},
  [OCTO_MEDIUM_RESOLUTION]: {w: 105, h: 61},
  [OCTO_LOW_RESOLUTION]: {w: 91, h: 56},

  [PUFFY_HIGH_RESOLUTION]: {w: 73, h: 70},
  [PUFFY_MEDIUM_RESOLUTION]: {w: 62, h: 60},
  [PUFFY_LOW_RESOLUTION]: {w: 52, h: 50},

  [DEAD_OCTO_HIGH_RESOLUTION]: {w: 122, h: 70},
  [DEAD_OCTO_MEDIUM_RESOLUTION]: {w: 105, h: 61},
  [DEAD_OCTO_LOW_RESOLUTION]: {w: 91, h: 56},

  [DEAD_PUFFY_HIGH_RESOLUTION]: {w: 73, h: 70},
  [DEAD_PUFFY_MEDIUM_RESOLUTION]: {w: 62, h: 60},
  [DEAD_PUFFY_LOW_RESOLUTION]: {w: 52, h: 50},
}

export const FISH_COLORMAP = {
  [OCTO]: "#FEB202",
  [DEAD_PUFFY] : "#FF0000",
  [PUFFY] : "#FEB202",
  [DEAD_OCTO] : "#FF0000",
}