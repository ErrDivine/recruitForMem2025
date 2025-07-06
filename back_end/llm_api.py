import requests
import json






def llm_action(messages, tools, function_mapper):
    """
    调用大模型并处理工具调用。

    :param messages: 对话历史
    :param tools: 提供给大模型的工具列表
    :param function_mapper: 一个将函数名映射到可执行函数的字典
    :return: 模型的最终回复和更新后的对话历史
    """
    #Config
    api_key = "sk-46f61c60859f4d19a1de714803d10f3e"
    url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {api_key}'}
    body = {
        'model': 'qwen-turbo',
        "input": {
            "messages": messages
        },
        "parameters": {
            "result_format": "message",
            "tools": tools
        }
    }

    #Get response
    print("--- Sending request to LLM ---")
    # print(json.dumps(body, indent=2, ensure_ascii=False))
    response = requests.post(url, headers=headers, json=body)
    
    response_json = response.json()
    if 'output' not in response_json:
        print(f"处理时发生错误: {response_json}")
        # 返回错误信息，而不是None
        return f"调用API时出错: {response_json.get('message', '未知错误')}", messages


    #Process response
    choice = response_json['output']['choices'][0]
    messages.append(choice['message'])

    #Diverge
    if choice.get('finish_reason') == 'tool_calls':
        print("--- LLM requested tool call ---")
        tool_call = choice['message']['tool_calls'][0]
        function_name = tool_call['function']['name']
        
        # 使用json.loads替代eval，更安全
        try:
            function_args = json.loads(tool_call['function']['arguments'])
            print(f"Tool: {function_name}, Args: {function_args}")
        except json.JSONDecodeError:
            # 有时模型返回的参数不是一个标准的JSON，而是一个裸字符串
            # 例如在只需要一个简单查询字符串的场景
            function_args = {'query': tool_call['function']['arguments']}
            print(f"Tool: {function_name}, Raw Args: {function_args['query']}")


        #config
        tool_info = {"name": function_name, "role": "tool"}
        
        #call
        if function_name in function_mapper:
            try:
                result = function_mapper[function_name](**function_args)
                tool_info["content"] = str(result) # 确保结果是字符串
            except Exception as e:
                print(f"Error executing tool {function_name}: {e}")
                tool_info["content"] = f"工具执行失败: {e}"
        else:
            print(f"Error: Tool '{function_name}' not found.")
            tool_info["content"] = f"错误：未找到名为 {function_name} 的工具。"
        
        print(f"--- Tool output: ---\n{tool_info['content']}\n----------------------")
        messages.append(tool_info)
    
        #continue
        return llm_action(messages, tools, function_mapper)
    
    elif choice.get('finish_reason') == 'stop':
        print("--- LLM returned final answer ---")
        #continue
        return choice['message']['content'],messages




def converse(messages):
    #query对话
    print("请与大模型对话:",flush=True)
    query = str(input())

    #退出
    if query == 'exit':
        print('goodbye!')
        return None



    #进行递归对话
    messages.append({"content":query,
                     "role":"user"
    })
    response = llm_action(messages)
    print(response[0],flush=True)
    converse(response[1])