#include <glad/glad.h>
#include <GLFW/glfw3.h>
// nanovg
#include "nanovg.h"
#define NANOVG_GL3_IMPLEMENTATION
#include "nanovg_gl.h"
#include "perf.h"
// my
#include "shaders.h"
#include "utils.h"
#include "camera.h"
#include "sysinfo.h"
// glm
#include <glm/glm.hpp>
#include <glm/gtc/type_ptr.hpp>
#include <glm/gtc/matrix_transform.hpp>
// stl
#include <random>
#include <chrono>
#include <vector>
#include <iostream>

float viewportWidth  = 0;
float viewportHeight = 0;
bool lbmPressed = false;
glm::vec2 cursorPos;
CCamera camera;
bool pause = false;

static void error_callback(int error, const char* description)
  { std::cerr << "GLFW::Error #" << error << ' ' << description << "\n"; }

void APIENTRY opengl_debug_callback(GLenum source, GLenum type, GLuint id, GLenum severity, GLsizei length, const GLchar *message, const void *userParam)
  {
    (void)source; (void)id; (void)severity; (void)length; (void)userParam;
    switch (type)
    {
      case GL_DEBUG_TYPE_ERROR:
        std::cerr << "GL::Error: ";
        break;
      case GL_DEBUG_TYPE_DEPRECATED_BEHAVIOR:
        std::cerr << "GL::Deprecated: ";
        break;
      case GL_DEBUG_TYPE_UNDEFINED_BEHAVIOR:
        std::cerr << "GL::Undefined: ";
        break;
      default:
        return;
    }
    std::cerr << message << std::endl;
  }

inline
bool isKeyPress(int waitKey, int key, int action)
  { return (key == waitKey && action == GLFW_PRESS); }

// glfw: process all input: query GLFW whether relevant keys are pressed/released this frame and react accordingly
static void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods)
  {
    (void)scancode; (void)mods;
    if (isKeyPress(GLFW_KEY_ESCAPE, key, action))
    {
      glfwSetWindowShouldClose(window, GLFW_TRUE);
    }
    if (isKeyPress(GLFW_KEY_P, key, action))
    { pause = !pause; }
  }

static void cursor_pos_callback(GLFWwindow* window, double xpos, double ypos)
  {
    (void)window;
    if (lbmPressed)
    {
      //always compute delta, cursorPos is the last mouse position
      const glm::vec2 delta = glm::vec2(xpos, ypos) - cursorPos;
      camera.mouseMove(delta.x, delta.y);
    }
    cursorPos = glm::vec2(xpos, ypos);
  }

void mouse_button_callback(GLFWwindow* window, int button, int action, int mods)
  {
    (void)window; (void)mods; (void)mods;
    if (button == GLFW_MOUSE_BUTTON_LEFT)
    { lbmPressed = (action == GLFW_PRESS); }
  }

void scroll_callback(GLFWwindow* window, double xoffset, double yoffset)
  {
    (void)window;
    camera.mouseScroll(xoffset, yoffset);
  }

// glfw: whenever the window size changed (by OS or user resize) this callback function executes
static void framebuffer_size_callback(GLFWwindow* window, int width, int height)
  {
    (void)window;
    viewportWidth = width;
    viewportHeight = height;
    // make sure the viewport matches the new window dimensions; note that width and
    // height will be significantly larger than specified on retina displays.
    glViewport(0, 0, width, height);
  }

template<typename T>
inline
GLsizeiptr size(const std::vector<T> &v)
  { return v.size() * sizeof(T); }

int main(int argc, char* argv[])
  {
    // ======================================================================================================
    // Init GLFW

    glfwSetErrorCallback(error_callback);

    glfwInit();
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_OPENGL_DEBUG_CONTEXT, GLFW_TRUE);
    glfwWindowHint(GLFW_RESIZABLE, GL_TRUE);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_DEBUG_CONTEXT, GLFW_TRUE);
    viewportWidth = 1024; viewportHeight = 768;

    GLFWwindow* window = glfwCreateWindow(viewportWidth, viewportHeight, "ComputeShader", nullptr, nullptr);
    if (window == nullptr)
    {
      std::cerr << "GLFW: Failed to create window\n";
      glfwTerminate();
      return -1;
    }

    glfwMakeContextCurrent(window);
    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_NORMAL);
    glfwSetKeyCallback(window, key_callback);
    glfwSetCursorPosCallback(window, cursor_pos_callback);
    glfwSetMouseButtonCallback(window, mouse_button_callback);
    glfwSetScrollCallback(window, scroll_callback);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    // ======================================================================================================
    // Init GLAD
    if (gladLoadGLLoader((GLADloadproc)glfwGetProcAddress) == 0)
    {
      std::cerr << "GLAD: Failed to initialize\n";
      return -1;
    }

    // Check system support compute shader
    if (!GLAD_GL_ARB_compute_shader)
    { std::cerr << "GL::Unsupported: ARB_compute_shader\n"; }
    if (!GLAD_GL_ARB_buffer_storage)
    { std::cerr << "GL::Unsupported: ARB_buffer_storage\n"; }

    sysinfo::printComputeShaderInfo();

    if (glDebugMessageCallback)
    { glDebugMessageCallback(opengl_debug_callback, nullptr); }
    else
    { std::cerr << "GL::Unsupported: glDebugMessageCallback()\n"; }

    int width, height;
    glfwMakeContextCurrent(window);
    glfwGetFramebufferSize(window, &width, &height);
    glViewport(0, 0, width, height);

    // ======================================================================================================
    // Load Shaders

    const std::string exe_fn = std::string(argv[0]);
    const std::string PATHEXE = exe_fn.substr(0, exe_fn.find_last_of(PathSeparator)+1);
    const std::string PATHSRS = PATHEXE + FixPath("shaders\\");
    const std::string PATHFNT = PATHEXE + FixPath("fonts\\");

    CShader shaderColor;
    shaderColor.load( {
      PATHSRS + FixPath("compute\\particles.vert"),
      PATHSRS + FixPath("compute\\particles.frag") }
    );

    CShader shaderCompute;
    shaderCompute.load( {
      PATHSRS + FixPath("compute\\particles.comp") }
    );

    // ======================================================================================================
    // Init Particles

    const int COMPUTE_GROUP_SIZE  = 256;

    int need_particles_count = 1000000;

    if (argc > 1)
    {
      try
      { need_particles_count = std::stoi(std::string(argv[1])); }
      catch (std::exception &e)
      { need_particles_count = 1000000; }
    }

    if (need_particles_count < COMPUTE_GROUP_SIZE)
    { need_particles_count = COMPUTE_GROUP_SIZE; }

    const int COMPUTE_GROUP_COUNT = need_particles_count / COMPUTE_GROUP_SIZE;

    const int PARTICLE_COUNT = COMPUTE_GROUP_COUNT * COMPUTE_GROUP_SIZE;
    const int ATTRACTOR_COUNT = 8;

    const std::string title = "ComputeShader. Particles " + std::to_string(PARTICLE_COUNT);
    glfwSetWindowTitle(window, title.c_str());

    // Positions (xyz) + Lifes (w)
    std::default_random_engine gen(static_cast<long unsigned int>(std::chrono::high_resolution_clock::now().time_since_epoch().count()));
    std::uniform_real_distribution<float> dis(-1.0f, 1.0f);

    std::vector<glm::vec4> data;
    data.reserve(PARTICLE_COUNT);
    for (size_t i = 0; i < PARTICLE_COUNT; ++i)
    {
      data.emplace_back(
        dis(gen) * 500.0f,
        dis(gen) * 500.0f,
        dis(gen) * 500.0f,
        dis(gen) * 0.5f + 0.5f);
    }

    GLuint vboPosLifes;
    glGenBuffers(1, &vboPosLifes);
    glBindBuffer(GL_ARRAY_BUFFER, vboPosLifes);
    glBufferData(GL_ARRAY_BUFFER, size(data), data.data(), GL_DYNAMIC_COPY);

    // Velocities
    for (auto &vel : data)
    {
      vel.x = dis(gen) * 0.2f;
      vel.y = dis(gen) * 0.2f;
      vel.z = dis(gen) * 0.2f;
      vel.w = 0.0f;
    }

    GLuint vboVelocities;
    glGenBuffers(1, &vboVelocities);
    glBindBuffer(GL_ARRAY_BUFFER, vboVelocities);
    glBufferData(GL_ARRAY_BUFFER, size(data), data.data(), GL_DYNAMIC_COPY);

    data.resize(0);

    // VAO Particles for draw
    GLuint vaoParticles;
    glGenVertexArrays(1, &vaoParticles);
    glBindVertexArray(vaoParticles);
    glBindBuffer(GL_ARRAY_BUFFER, vboPosLifes);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, sizeof(glm::vec4), nullptr);
    glEnableVertexAttribArray(0);
    glBindVertexArray(0);

    camera.mode = CCamera::Mode::Orbit;
    camera.zfar = 5000.0f;
    camera.lookat(glm::vec3(0.0f, 0.0f, -3000.0f), glm::vec3(0.0f));

    // ======================================================================================================
    // Init NanoVG
    NVGcontext* vg = nullptr;
    //vg = nvgCreateGL3(NVG_ANTIALIAS | NVG_STENCIL_STROKES);
    vg = nvgCreateGL3(0);
    if (vg == nullptr)
    { std::cerr << "NVG: Failed to initialize\n"; }

    const std::string font = PATHFNT + "Roboto-Regular.ttf";
    if (nvgCreateFont(vg, "sans", font.c_str()) == -1)
    { std::cerr << "NVG: Failed to create font\n"; }

    PerfGraph fps, cpuGraph, gpuGraph;
    initGraph(&fps, GRAPH_RENDER_FPS, "Frame Time");
    initGraph(&cpuGraph, GRAPH_RENDER_MS, "CPU Time");

    // ======================================================================================================
    // Main Loop

    glfwSetTime(0.0);

    while(glfwWindowShouldClose(window) == 0)
    {
      static int frameCount = 0;
      ++frameCount;

      glEnable(GL_DEPTH_TEST);
      glDisable(GL_CULL_FACE);
      glEnable(GL_BLEND);
      glBlendFunc(GL_ONE, GL_ONE);
      glPointSize(1.0f);

      const auto deltaTime = static_cast<float>(glfwGetTime());
      glfwSetTime(0.0);

      glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

      glm::mat4 projection = glm::perspective(glm::radians(camera.fov), viewportWidth/viewportHeight, camera.znear, camera.zfar);
      glm::mat4 view = camera.view;
      glm::mat4 model(1.0f);

      // ====================================================================================================
      // Cursor position from Screen space to World space

      const float x_ndc = 2.0f * cursorPos.x / viewportWidth - 1.0f;
      const float y_ndc = 1.0f - 2.0f * cursorPos.y / viewportHeight;

      const float f = camera.zfar;
      const float n = camera.znear;
      const float ze = -glm::length(camera.position);
      const float z_ndc = (-ze * (f + n) / (f - n) - 2.0f * f * n / (f - n)) / (-ze);

      glm::vec4 cur_ndc = {x_ndc, y_ndc, z_ndc, 1.0f};
      const glm::mat4 mat = glm::inverse(projection * view);
      glm::vec4 cur_ws = mat * cur_ndc;

      cur_ws /= cur_ws.w;

      if (!pause)
      {
        glm::vec3 forcePos(0.0f);

        // Force position = Mouse in World space
        forcePos = cur_ws;

        shaderCompute.use();
        shaderCompute.setFloat("DeltaTime", deltaTime);
        shaderCompute.setVec3fv("ForcePos", glm::value_ptr(forcePos));
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, vboPosLifes);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, vboVelocities);
        glDispatchCompute(COMPUTE_GROUP_COUNT, 1, 1);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
      }

      // ====================================================================================================
      // Draw particles

      glm::mat4 mvp = projection * view * model;

      shaderColor.use();
      shaderColor.setMat4fv("MVP", glm::value_ptr(mvp));
      glBindVertexArray(vaoParticles);
      glDrawArrays(GL_POINTS, 0, PARTICLE_COUNT);
      glBindVertexArray(0);

      // ====================================================================================================
      // Draw NanoVG
      nvgBeginFrame(vg, viewportWidth, viewportHeight, 1.0f);
      renderGraph(vg, 5, 5, &fps);
      renderGraph(vg, 5, 5+35+5, &cpuGraph);
      nvgEndFrame(vg);
      updateGraph(&fps, deltaTime);
      updateGraph(&cpuGraph, deltaTime);

      // Restore before use NanoVG
      /// TODO: improve overhead switch states
      glBindFramebuffer(GL_FRAMEBUFFER, 0);
      glEnable(GL_DEPTH_TEST);
      glEnable(GL_STENCIL_TEST);
      glStencilFunc(GL_ALWAYS, 1, 255);
      glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE);
      glStencilMask(255);
      glClearStencil(0);
      glEnable(GL_CULL_FACE);
      glCullFace(GL_BACK);
      glFrontFace(GL_CCW);
      glEnable(GL_BLEND);
      glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

      // glfw: swap buffers and poll IO events (keys pressed/released, mouse moved etc.)
      glfwSwapBuffers(window);
      glfwPollEvents();
    }

    glDeleteBuffers(1, &vboPosLifes);
    glDeleteBuffers(1, &vboVelocities);
    glDeleteVertexArrays(1, &vaoParticles);

    // glfw: terminate, clearing all previously allocated GLFW resources
    glfwDestroyWindow(window);
    glfwTerminate();

    return 0;
  }
