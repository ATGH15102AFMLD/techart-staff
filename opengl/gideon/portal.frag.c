#version 410 core

out vec4 FragColor;

uniform vec3 Origin = vec3(0.0);
uniform vec3 Eye = vec3(0.0);
uniform vec3 PortalColor_1 = vec3(0.423, 1.0, 0.0);
uniform vec3 PortalColor_2 = vec3(0.000, 0.8, 0.0);
uniform vec3 AnotherWorldColor = vec3(1.0, 0.488, 1.0);
uniform float AnotherWorldGlow = 3.0;
uniform float ElapsedTime = 0.0;

uniform sampler2D   TexMask;
uniform sampler2D   TexNoise;
uniform samplerCube TexWorld;
uniform sampler2D   TexCustomStencil;

struct VSData
{
  vec2 positionLS;    // Local XZ-position
  vec3 positionWS;    // World position
  vec3 normalWS;
};

in VSData vs_data;

const float PI = 3.141592653589;

void main()
{
  float stencil = 1.0 - texelFetch(TexCustomStencil, ivec2(gl_FragCoord.xy), 0).r;

  float x = vs_data.positionLS.x;
  float y = vs_data.positionLS.y;

  float t = atan(x, y);

  float u = t * 1.0 / PI * 0.5 + 0.5;
  float v = 1.0 - length(vs_data.positionLS);

  vec2 uv = vec2(u * 2.0, v + sin(ElapsedTime) * 0.02);

  vec4 masks = texture(TexMask, uv);

  v = v * 2.0 + ElapsedTime * 0.15;
  float noise = texture(TexNoise, vec2(u, v)).r;
  vec3 rgb = mix(PortalColor_1, PortalColor_2, noise);

  float alpha = masks.r;

  if (gl_FrontFacing)
  {
      vec3 incident = normalize(Eye - vs_data.positionWS);
      vec3 uvw = reflect(incident, vs_data.normalWS);

      vec3 color = texture(TexWorld, uvw).rgb;

      color = PortalColor_1 * (1-masks.b) + masks.b * color * AnotherWorldColor * AnotherWorldGlow;

      float m = masks.r * masks.g;
      rgb = mix(color, rgb, m);
      alpha = (stencil + masks.g) * masks.r;
  }

  FragColor = vec4(rgb, alpha);
}
