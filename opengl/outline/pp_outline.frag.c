// Outline with Stencil & Sobel

#version 330 core

out vec4 FragColor;

noperspective in vec2 UV;

uniform       vec3 Color;
uniform      float KernelV[9] = float[9](1.0,  2.0,  1.0,  0.0,  0.0,  0.0, -1.0, -2.0, -1.0);
uniform      float KernelH[9] = float[9](1.0,  0.0, -1.0,  2.0,  0.0, -2.0,  1.0,  0.0, -1.0);

uniform  sampler2D ColorTexture;
uniform usampler2D StencilTexture;

void SampleSceneTextureNeighbourUVs(const vec2 center, out vec2 uvs[9])
{
  vec2 texel_size = vec2(1.0) / vec2(textureSize(ColorTexture, 0));

  const vec2 offset[9] = vec2[9](
    vec2(-1.0,  1.0),
    vec2( 0.0,  1.0),
    vec2( 1.0,  1.0),

    vec2(-1.0,  0.0),
    vec2( 0.0,  0.0),
    vec2( 1.0,  0.0),

    vec2(-1.0, -1.0),
    vec2( 0.0, -1.0),
    vec2( 1.0, -1.0)
  );

  for (int i = 0; i < 9; ++i)
  {
    uvs[i] = center + offset[i] * texel_size;
  }
}

float ConvolveTexture(const in float core[9], const in float pixels[9])
{
  float weight = 0.0;
  for (int i = 0; i < 9; ++i)
  {
    weight += pixels[i] * core[i];
  }
  return weight;
}

void main()
{
  vec2 nuvs[9];
  SampleSceneTextureNeighbourUVs(UV, nuvs);

  float pixels[9];
  for (int i = 0; i < 9; ++i)
  {
    uint stencil_index = texture(StencilTexture, nuvs[i]).r;
    stencil_index = clamp(stencil_index, 0U, 1U);
    pixels[i] = float(stencil_index);
  }

  // Sobel Operator - Vertical
  float weightv = ConvolveTexture(KernelV, pixels);

  // Sobel Operator - Horizontal
  float weighth = ConvolveTexture(KernelH, pixels);

  float l = length(vec2(weightv, weighth));

  const float maxl = 0.25;

  FragColor = mix(texture(ColorTexture, UV), vec4(Color, 1.0), l*maxl);
}