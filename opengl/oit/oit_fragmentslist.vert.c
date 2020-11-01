#version 430 core

out float Depth;

layout (location = 0) in vec3 vert_position;

layout(std140)
uniform PerObject
{
  mat4 MVP_Matrix;   // Projection * View * Model;
  mat4 MV_Matrix;    // View * Model
  mat4 NV_Matrix;    // View * mat4(mat3(transpose(inverse(Model))))
  mat4 P_Matrix;     // Projection
  mat4 V_Matrix;     // View
  mat4 M_Matrix;     // Model
};

void main()
{
  gl_Position = MVP_Matrix * vec4(vert_position, 1.0);
  Depth = gl_Position.z;
}
