#version 430 core

// Default block dimension is 1
layout (local_size_x = 256) in;

layout (std430, binding = 0)
buffer PosLifeBuf
{
  vec4 posLifes[];
};

layout (std430, binding = 1)
buffer VelocityBuf
{
  vec4 velocities[];
};

uniform float DeltaTime;
uniform vec3  ForcePos;

highp float rand(vec2 co)
{
  highp const float a = 12.9898;
  highp const float b = 78.233;
  highp const float c = 43758.5453;
  highp float dt = dot(co.xy ,vec2(a,b));
  highp float sn = mod(dt, 3.14);
  return fract(sin(sn) * c);
}

vec3 calcForceFor(const vec3 forcePos, const vec3 pos)
{
  const float gauss = 10000.0;
  const float e = 2.71828183;
  const float k_weak = 1.0;
  vec3 dir = forcePos - pos;
  float g = pow(e, -pow(length(dir), 2) / gauss);
  return normalize(dir) * k_weak * (1 + mod(rand(dir.xy), 10) - mod(rand(dir.yz), 10)) / 10.0 * g;
}

void main()
{
# define ID gl_GlobalInvocationID.x

  const vec3 forcePos = ForcePos;
  
  vec3 pos = posLifes[ID].xyz;
  vec4 vel = velocities[ID];
  float life = posLifes[ID].w;
  
  vec3 f = calcForceFor(forcePos, pos) + rand(pos.xz)/100.0;
  
  const float k_v = 1.5;
  float dt = DeltaTime * 100.0;
  vec3 v = normalize(vel.xyz + (f * dt)) * k_v;
  
  v += (forcePos - pos) * 0.00005;
  
  vec3 s = pos + v * dt;
  
  life -= 0.0001 * dt;
  
  if (life <= 0)
  {
    s = -s + rand(s.xy) * 20.0 - rand(s.yz) * 20.0;
    life = 0.99f;
  }
  
  posLifes[ID].w = life;
  posLifes[ID].xyz = s;
  velocities[ID] = vec4(v, vel.w);
}


