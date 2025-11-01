# Tool Calling

**URL:** https://v6.ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling

## Overview

Tools are objects that can be called by the model to perform a specific task. AI SDK Core tools contain three elements:

- **`description`**: An optional description of the tool that can influence when the tool is picked.
- **`inputSchema`**: A Zod schema or JSON schema that defines the input parameters. The schema is consumed by the LLM and used to validate the LLM tool calls.
- **`execute`**: An optional async function that is called with the inputs from the tool call. It produces a value of type RESULT (generic type).

## Basic Tool Definition

Use the `tool` helper function to infer the types of the execute parameters:

```typescript
import { z } from 'zod';
import { generateText, tool } from 'ai';

const result = await generateText({
  model: 'openai/gpt-4o',
  tools: {
    weather: tool({
      description: 'Get the weather in a location',
      inputSchema: z.object({
        location: z.string().describe('The location to get the weather for'),
      }),
      execute: async ({ location }) => ({
        location,
        temperature: 72 + Math.floor(Math.random() * 21) - 10,
      }),
    }),
  },
  prompt: 'What is the weather in San Francisco?',
});
```

When a model uses a tool, it is called a **"tool call"** and the output of the tool is called a **"tool result"**.

## Multi-Step Calls (using stopWhen)

With the `stopWhen` setting, you can enable multi-step calls in `generateText` and `streamText`. When `stopWhen` is set and the model generates a tool call, the AI SDK will trigger a new generation passing in the tool result until there are no further tool calls or the stopping condition is met.

### Example: Two-step process

```typescript
import { z } from 'zod';
import { generateText, tool, stepCountIs } from 'ai';

const { text, steps } = await generateText({
  model: 'openai/gpt-4o',
  tools: {
    weather: tool({
      description: 'Get the weather in a location',
      inputSchema: z.object({
        location: z.string().describe('The location to get the weather for'),
      }),
      execute: async ({ location }) => ({
        location,
        temperature: 72 + Math.floor(Math.random() * 21) - 10,
      }),
    }),
  },
  stopWhen: stepCountIs(5), // stop after a maximum of 5 steps if tools were called
  prompt: 'What is the weather in San Francisco?',
});
```

**Steps:**
1. The prompt 'What is the weather in San Francisco?' is sent to the model.
2. The model generates a tool call.
3. The tool call is executed.
4. The tool result is sent to the model.
5. The model generates a response considering the tool result.

## Steps

To access intermediate tool calls and results, use the `steps` property in the result object or the `streamText` onFinish callback. It contains all the text, tool calls, tool results, and more from each step.

```typescript
const { steps } = await generateText({
  model: openai('gpt-4o'),
  stopWhen: stepCountIs(10),
  // ...
});

// extract all tool calls from the steps:
const allToolCalls = steps.flatMap(step => step.toolCalls);
```

## onStepFinish Callback

Triggered when a step is finished, i.e. all text deltas, tool calls, and tool results for the step are available:

```typescript
import { generateText } from 'ai';

const result = await generateText({
  // ...
  onStepFinish({ text, toolCalls, toolResults, finishReason, usage }) {
    // your own logic, e.g. for saving the chat history or recording usage
  },
});
```

## prepareStep Callback

Called before a step is started. Can be used to provide different settings for a step, including modifying the input messages:

```typescript
const result = await generateText({
  // ...
  prepareStep: async ({ model, stepNumber, steps, messages }) => {
    if (stepNumber === 0) {
      return {
        model: modelForThisParticularStep,
        toolChoice: { type: 'tool', toolName: 'tool1' },
        activeTools: ['tool1'],
      };
    }
    // when nothing is returned, the default settings are used
  },
});
```

### Message Modification for Longer Agentic Loops

For longer agentic loops, you can use the messages parameter to modify the input messages for each step (useful for prompt compression):

```typescript
prepareStep: async ({ stepNumber, steps, messages }) => {
  // Compress conversation history for longer loops
  if (messages.length > 20) {
    return {
      messages: messages.slice(-10),
    };
  }

  return {};
},
```

## Response Messages

Both `generateText` and `streamText` have a `response.messages` property that you can use to add the assistant and tool messages to your conversation history:

```typescript
import { generateText, ModelMessage } from 'ai';

const messages: ModelMessage[] = [
  // ...
];

const { response } = await generateText({
  // ...
  messages,
});

// add the response messages to your conversation history:
messages.push(...response.messages);
```

## Dynamic Tools

AI SDK Core supports dynamic tools for scenarios where tool schemas are not known at compile time:

```typescript
import { dynamicTool } from 'ai';
import { z } from 'zod'

;

const customTool = dynamicTool({
  description: 'Execute a custom function',
  inputSchema: z.object({}),
  execute: async input => {
    // input is typed as 'unknown'
    // You need to validate/cast it at runtime
    const { action, parameters } = input as any;

    // Execute your dynamic logic
    return { result: `Executed ${action}` };
  },
});
```

## Tool Choice

You can use the `toolChoice` setting to influence when a tool is selected:

- `auto` (default): the model can choose whether and which tools to call.
- `required`: the model must call a tool. It can choose which tool to call.
- `none`: the model must not call tools
- `{ type: 'tool', toolName: string }`: the model must call the specified tool

```typescript
const result = await generateText({
  model: 'openai/gpt-4o',
  tools: {
    weather: tool({
      description: 'Get the weather in a location',
      inputSchema: z.object({
        location: z.string().describe('The location to get the weather for'),
      }),
      execute: async ({ location }) => ({
        location,
        temperature: 72 + Math.floor(Math.random() * 21) - 10,
      }),
    }),
  },
  toolChoice: 'required', // force the model to call a tool
  prompt: 'What is the weather in San Francisco?',
});
```

## Tool Execution Options

When tools are called, they receive additional options as a second parameter.

### Tool Call ID

```typescript
execute: async (args, { toolCallId }) => {
  // return e.g. custom status for tool call
  writer.write({
    type: 'data-tool-status',
    id: toolCallId,
    data: {
      name: 'myTool',
      status: 'in-progress',
    },
  });
  // ..
.
}
```

### Messages

```typescript
execute: async (args, { messages }) => {
  // use the message history in e.g. calls to other language models
  return { ... };
}
```

### Abort Signals

```typescript
execute: async ({ location }, { abortSignal }) => {
  return fetch(
    `https://api.weatherapi.com/v1/current.json?q=${location}`,
    { signal: abortSignal }, // forward the abort signal to fetch
  );
}
```

### Context (experimental)

```typescript
const result = await generateText({
  // ...
  tools: {
    someTool: tool({
      // ...
      execute: async (input, { experimental_context: context }) => {
        const typedContext = context as { example: string };
        // ...
      },
    }),
  },
  experimental_context: { example: '123' },
});
```

## Error Handling

The AI SDK has three tool-call related errors:

- **NoSuchToolError**: the model tries to call a tool that is not defined in the tools object
- **InvalidToolInputError**: the model calls a tool with inputs that do not match the tool's input schema
- **ToolCallRepairError**: an error that occurred during tool call repair

### generateText

```typescript
try {
  const result = await generateText({
    //...
  });
} catch (error) {
  if (NoSuchToolError.isInstance(error)) {
    // handle the no such tool error
  } else if (InvalidToolInputError.isInstance(error)) {
    // handle the invalid tool inputs error
  } else {
    // handle other errors
  }
}
```

Tool execution errors are available in the result steps:

```typescript
const { steps } = await generateText({
  // ...
});

const toolErrors = steps.flatMap(step =>
  step.content.filter(part => part.type === 'tool-error'),
);

toolErrors.forEach(toolError => {
  console.log('Tool error:', toolError.error);
  console.log('Tool name:', toolError.toolName);
  console.log('Tool input:', toolError.input);
});
```

## Extracting Tools

For code organization, you can extract tools into separate files:

```typescript
// tools/weather-tool.ts
import { tool } from 'ai';
import { z } from 'zod';

// the `tool` helper function ensures correct type inference:
export const weatherTool = tool({
  description: 'Get the weather in a location',
  inputSchema: z.object({
    location: z.string().describe('The location to get the weather for'),
  }),
  execute: async ({ location }) => ({
    location,
    temperature: 72 + Math.floor(Math.random() * 21) - 10,
  }),
});
```

## MCP Tools

The AI SDK supports connecting to Model Context Protocol (MCP) servers to access their tools. MCP enables your AI applications to discover and use tools across various services through a standardized interface.

### AI SDK Tools vs MCP Tools

In most cases, you should define your own AI SDK tools for production applications. They provide full control, type safety, and optimal performance. MCP tools are best suited for rapid development iteration and scenarios where users bring their own tools.

| Aspect | AI SDK Tools | MCP Tools |
|--------|-------------|-----------|
| Type Safety | Full static typing end-to-end | Dynamic discovery at runtime |
| Execution | Same process as your request (low latency) | Separate server (network overhead) |
| Prompt Control | Full control over descriptions and schemas | Controlled by MCP server owner |
| Schema Control | You define and optimize for your model | Controlled by MCP server owner |
| Best For | Production applications requiring control and performance | Development iteration, user-provided tools |

