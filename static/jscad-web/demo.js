const jscad = require('@jscad/modeling')
const { cylinder, cuboid } = jscad.primitives
const { translate, rotateX } = jscad.transforms
const { colorize } = jscad.colors
const { subtract } = jscad.booleans

const getParameterDefinitions = () => {
  return [
    { name: 'tankRadius', type: 'number', initial: 2.5, caption: '热压罐半径(m):' },
    { name: 'tankLength', type: 'number', initial: 12, caption: '热压罐长度(Y轴)(m):' },
    { name: 'minDistance', type: 'number', initial: 1.5, caption: '最小安全距离(m):' },
    { name: 'skinX', type: 'number', initial: 0, min: -2, max: 2, step: 0.1, caption: '蒙皮X位置:' },
    { name: 'skinY', type: 'number', initial: 0, min: -5, max: 5, step: 0.1, caption: '蒙皮Y位置:' },
    { name: 'plateX', type: 'number', initial: 0, min: -2, max: 2, step: 0.1, caption: '平板X位置:' },
    { name: 'plateY', type: 'number', initial: 0, min: -5, max: 5, step: 0.1, caption: '平板Y位置:' }
  ]
}

const main = (params) => {
  // 坐标系定义：
  // Y轴 - 热压罐中心轴线 (长度方向，12米)
  // Z轴 - 高度方向 (垂直方向)
  // X轴 - 宽度方向
  
  // 热压罐参数
  const tankRadius = params.tankRadius
  const tankLength = params.tankLength
  const wallThickness = 0.1 // 罐壁厚度
  
  // 安全距离计算
  const minZ = -tankRadius + wallThickness + params.minDistance

  // 创建热压罐 (Y轴为长度方向)
  const outerTank = rotateX(Math.PI/2, cylinder({
    radius: tankRadius,
    height: tankLength,
    segments: 64
  }))
  
  const innerTank = rotateX(Math.PI/2, cylinder({
    radius: tankRadius - wallThickness,
    height: tankLength + 0.2,
    segments: 64
  }))
  
  const tank = subtract(
    outerTank,
    translate([0, -0.1, 0], innerTank)
  )

  // 创建蒙皮 (8米长Y轴，1.8米宽X轴，0.05米厚Z轴)
  // 位置完全独立：skinX, skinY
  const skin = colorize([1, 0.8, 0.6, 0.8],
    translate([
      params.skinX, 
      params.skinY,
      minZ + 0.025 // 0.05/2 = 0.025
    ],
    cuboid({
      size: [
        1.8,   // X轴宽度
        8,     // Y轴长度 (8米)
        0.05   // Z轴厚度
      ]
    }))
  )

  // 创建平板 (2米长Y轴，1.2米宽X轴，0.1米厚Z轴)
  // 位置完全独立：plateX, plateY
  const plate = colorize([0.7, 0.7, 1, 0.8],
    translate([
      params.plateX,
      params.plateY,
      minZ + 0.05 // 0.1/2 = 0.05
    ],
    cuboid({
      size: [
        1.2,   // X轴宽度
        2,     // Y轴长度 (2米)
        0.1    // Z轴厚度
      ]
    }))
  )

  // 组装所有部件
  return [
    colorize([0.7, 0.7, 0.7, 0.3], tank),
    skin,
    plate
  ]
}

module.exports = { main, getParameterDefinitions }