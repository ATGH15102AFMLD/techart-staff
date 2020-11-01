#version 410 core

layout (location = 0) out vec4  Color;
layout (location = 1) out float CustomStencil;

uniform vec3 Eye = vec3(0.0);                // Camera position WS
uniform vec3 EyeForward = vec3(0.0);         // Camera forward WS
uniform vec3 Origin = vec3(0.0);             // Portal origin
uniform vec3 Forward = vec3(0.0, 0.0, 1.0);  // Portal forward
uniform float Radius = 0.90;                 // Portal radius

struct VSData
{
  vec3 positionWS;    // World position
  vec3 normalWS;
};

in VSData vs_data;

struct LightingResult
{
    vec3 diffuse;
    vec3 specular;
};

vec3 DoDiffuse(vec3 lightColor, vec3 L, vec3 N)
{
  float NdotL = max(dot(N, L), 0.0);
  return lightColor * NdotL;
}

vec3 DoSpecular(vec3 lightColor, float materialSpecularPower, vec3 V, vec3 L, vec3 N)
{
  vec3 R = reflect(-L, N);
  float RdotV = max(dot(V, R), 0.0);
  return lightColor * pow(RdotV, materialSpecularPower);
}

LightingResult DoDirectionalLight(vec3 lightColor, float materialSpecularPower, vec3 V, vec3 P, vec3 N)
{
  LightingResult result;

  vec3 lightDir = EyeForward;
  float lightIntensity = 1.0;

  vec3 L = normalize(-lightDir);

  result.diffuse = DoDiffuse(lightColor, L, N) * lightIntensity;
  result.specular = DoSpecular(lightColor, materialSpecularPower, V, L, N) * lightIntensity;

  return result;
}

vec4 DoLighting()
{
  vec3 diffuse = vec3(0.6, 0.5, 0.0);
  vec3 ambient = vec3(0.0) * diffuse;
  vec3 specular = diffuse;

  vec3 N = normalize(vs_data.normalWS);
  vec3 P = vs_data.positionWS;

  vec3 V = normalize(Eye - P);

  vec3 lightColor = vec3(1.0);
  float materialSpecularPower = 1.0;

  LightingResult lit = DoDirectionalLight(lightColor, materialSpecularPower, V, P, N);

  diffuse  *= lit.diffuse;
  specular *= lit.specular;

  return vec4(ambient + diffuse + specular, 1.0);
}

vec3 createThirdOrtogonalVector(vec3 origin, vec3 zvector, vec3 transform)
{
  const vec3 right = vec3(1.0, 0.0, 0.0);

  vec3 z = normalize(zvector);
  vec3 y = cross(z, right);
  vec3 x = normalize(cross(y, z));

  y = normalize(y);

  return (transform - origin) * mat3(x, y, z);
}

void main()
{
  vec3 forward = normalize(Forward);

  float alpha = createThirdOrtogonalVector(Origin, forward, Eye).z;
  alpha = step(0.0, alpha);

  float a = createThirdOrtogonalVector(Origin, forward, vs_data.positionWS).z;
  a = step(0.0, a);

  vec3 toEye = normalize(vs_data.positionWS - Eye);
  vec3 r = Eye + dot((Origin - Eye), forward) / dot(toEye, forward) * toEye;
  float d = distance(Origin, r);
  float b = step(Radius, d);

  a = min(a, b);
  b = max(a, 1.0 - b);

  float drop = mix(a, b, alpha);

  if (drop < 0.1) discard;

  Color = DoLighting();
  CustomStencil = 1.0;
}
