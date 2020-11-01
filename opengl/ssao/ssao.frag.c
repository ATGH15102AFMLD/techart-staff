// Based on UNIGINE2 SSAO

#version 410 core

#define SAMPLE_COUNT_MAX 64

layout (location = 0) out vec3 FragColor;

noperspective in vec2 UV;

uniform sampler2D TexPosition;
uniform sampler2D TexNormal;
uniform sampler2DArray TexNoise;
uniform sampler1D TexSamples;

uniform uint FrameNum = 0;

uniform float Radius = 0.125;
uniform float Intensity = 3.0;
uniform float Power = 1.0;
uniform float MaxClamp = 0.98;

// ===========================================================================

vec3 decodeNormal_LAEAP(vec2 e)
{
  e = e * 4.0 - 2.0;
  float d = dot(e, e);
  vec3 n;
  n.xy = e.xy * sqrt(1.0 - d * 0.25);
  n.z = 1.0 - d * 0.5;
  return n;
}

vec3 getNormal(sampler2D sampler, ivec2 p)
{
  vec4 e = texelFetch(sampler, p, 0);
  return normalize(decodeNormal_LAEAP(e.rg));
}

// ===========================================================================

uniform vec2 Offset[] = vec2[](
  normalize(vec2( 0.5,  0.5)),
  normalize(vec2(-0.5,  0.5)),
  normalize(vec2( 0.5, -0.5)),
  normalize(vec2(-0.5, -0.5))
);

uniform vec2 Halton8[] = vec2[](
  normalize(vec2(1.0 /  2.0, 1.0 / 3.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(1.0 /  4.0, 2.0 / 3.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(3.0 /  4.0, 1.0 / 9.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(1.0 /  8.0, 4.0 / 9.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(5.0 /  8.0, 7.0 / 9.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(3.0 /  8.0, 2.0 / 9.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(7.0 /  8.0, 5.0 / 9.0) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(1.0 / 16.0, 8.0 / 9.0) * 2.0 - vec2(1.0, 1.0))
);

uniform vec2 Halton16[] = vec2[](
  normalize(vec2(0.375, 0.4375) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.625, 0.0625) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.875, 0.1875) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.125, 0.0625) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.375, 0.6875) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.875, 0.4375) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.625, 0.5625) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.375, 0.9375) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.625, 0.3125) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.125, 0.5625) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.125, 0.8125) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.375, 0.1875) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.875, 0.9375) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.875, 0.6875) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.125, 0.3125) * 2.0 - vec2(1.0, 1.0)),
  normalize(vec2(0.625, 0.8125) * 2.0 - vec2(1.0, 1.0))
);

#define SSAO_PRESET_MED

#if defined(SSAO_PRESET_LOW)
  #define SSAO_SAMPLES Offset
  #define SSAO_SAMPLES_SIZE 4
  #define SSAO_RAY_STEPS 4
#elif defined(SSAO_PRESET_MED)
  #define SSAO_SAMPLES Halton8
  #define SSAO_SAMPLES_SIZE 8
  #define SSAO_RAY_STEPS 4
#elif defined(SSAO_PRESET_HIGH)
  #define SSAO_SAMPLES Halton16
  #define SSAO_SAMPLES_SIZE 16
  #define SSAO_RAY_STEPS 4
#elif defined(SSAO_PRESET_ULTRA)
  #define SSAO_SAMPLES Halton16
  #define SSAO_SAMPLES_SIZE 16
  #define SSAO_RAY_STEPS 8
#endif

float pow2(in float value){
  return value * value;
}

void main()
{
  float frag_color = 1.0;

  vec4 noise = texelFetch(TexNoise, ivec3(mod(gl_FragCoord.xy, 256), FrameNum % 8), 0);

  vec4 viewport;
  viewport.xy = textureSize(TexPosition, 0);
  viewport.zw = 1.0 / viewport.xy;

  vec2 uv = UV + noise.x * 1e-4;

  vec3 position = texelFetch(TexPosition, ivec2(uv * viewport.xy), 0).xyz;

  if (position.z != 0.0)
  {
    float depth = length(position);

    vec3 normal = getNormal(TexNormal, ivec2(uv * viewport.xy));

    frag_color = 0.0;

    float ssao_radius = (noise.x * 0.7 + 0.3) * Radius;

    float min_radius = 2.0 * min(viewport.w, viewport.z);

    float aspect_v = viewport.y * viewport.z;

    for(uint i = 0; i < SSAO_SAMPLES_SIZE; ++i)
    {
      vec2 offset = SSAO_SAMPLES[i];

      offset.x *= aspect_v;

      float size = 0.0;
      for(int j = 0; j < SSAO_RAY_STEPS; j++)
      {
        float r = ssao_radius * pow2(size) + min_radius;

        vec2 uv_ao = uv + offset * r;
        vec3 delta = texelFetch(TexPosition, ivec2(uv_ao * viewport.xy), 0).xyz - position;

        // 0.15 ~ cos(81.37deg)
        frag_color += clamp(dot(normalize(delta), normal) - 0.15, 0.0, 1.0) * clamp(1.0 - length(delta) / (depth * sqrt(r)), 0.0, 1.0);

        size += 1.0 / SSAO_RAY_STEPS;
      }
    }

    frag_color *= 1.0 / SSAO_SAMPLES_SIZE * 1.0 / SSAO_RAY_STEPS;
    frag_color = clamp(1.0 - frag_color * Intensity, 0.0, 1.0);
    frag_color = pow(frag_color, Power);
  }

  FragColor = vec3(frag_color);
}
