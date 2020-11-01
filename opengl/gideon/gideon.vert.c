#version 410 core

layout (location = 0) in vec3 vert_position;
layout (location = 1) in vec3 vert_tangent;
layout (location = 2) in vec3 vert_normal;
layout (location = 3) in vec2 vert_texCoord;
layout (location = 4) in vec3 vert_binormal;

layout(std140)
uniform PerObject
{
  mat4 MVP_Matrix;    // Projection * View * Model;
  mat4 MV_Matrix;     // View * Model
  mat4 NV_Matrix;     // View * mat4(mat3(transpose(inverse(Model))))
  mat4 P_Matrix;      // Projection
  mat4 V_Matrix;      // View
  mat4 M_Matrix;      // Model
};

uniform vec3 Offset = vec3(0.0);

struct VSData
{
  vec3 positionWS;    // World position
  vec3 normalWS;
};

out VSData vs_data;

void main()
{
  vec3 pos = Offset + vert_position;

  gl_Position = MVP_Matrix * vec4(pos, 1.0);

  vs_data.positionWS = (M_Matrix * vec4(pos, 1.0)).xyz;
  vs_data.normalWS = mat3(transpose(inverse(M_Matrix))) * vert_normal;
}
