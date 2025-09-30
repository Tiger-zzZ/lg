import { SearchOutlined, MessageOutlined, FileTextOutlined, BarChartOutlined } from '@ant-design/icons';
import { ReactNode } from 'react';

/**
 * Agent配置项类型
 */
export type ConfigFieldType = 'slider' | 'number' | 'input' | 'select' | 'textarea';

export interface ConfigField {
  type: ConfigFieldType;
  label: string;
  default: any;
  description: string;
  tooltip?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ label: string; value: any }>;
  placeholder?: string;
  required?: boolean;
}

/**
 * Agent类型配置模式
 */
export interface AgentConfigSchema {
  [key: string]: ConfigField;
}

/**
 * Agent类型信息
 */
export interface AgentTypeInfo {
  name: string;
  icon: ReactNode;
  color: string;
  description: string;
  detailedDescription: string;
  capabilities: string[];
  usageExample: string;
  useCases: string[];
  configSchema: AgentConfigSchema;
  configTemplates?: Array<{
    name: string;
    description: string;
    config: Record<string, any>;
  }>;
}

/**
 * Agent类型元数据
 */
export const AGENT_TYPE_INFO: Record<string, AgentTypeInfo> = {
  search: {
    name: 'Search Agent',
    icon: SearchOutlined,
    color: '#1890ff',
    description: '搜索助手 - 专门用于文档搜索和信息检索',
    detailedDescription: '基于语义搜索和关键词匹配的智能文档检索助手，能够在知识库中快速找到相关信息，支持混合搜索和多文档召回。',
    capabilities: [
      '语义搜索',
      '关键词检索',
      '混合搜索',
      '文档召回',
      'Top-K结果',
      '相似度排序'
    ],
    usageExample: '帮我搜索关于Python异步编程的文档',
    useCases: [
      '知识库搜索',
      '文档查找',
      '信息检索',
      '内容发现'
    ],
    configSchema: {
      top_k: {
        type: 'number',
        label: '返回结果数量',
        default: 5,
        description: '搜索返回的最大结果数',
        tooltip: '设置每次搜索最多返回多少个文档',
        min: 1,
        max: 20,
        required: true
      },
      semantic_weight: {
        type: 'slider',
        label: '语义搜索权重',
        default: 0.6,
        description: '语义搜索在混合搜索中的权重（0-1）',
        tooltip: '值越大，越依赖语义理解；值越小，越依赖关键词匹配',
        min: 0,
        max: 1,
        step: 0.1,
        required: true
      },
      keyword_weight: {
        type: 'slider',
        label: '关键词搜索权重',
        default: 0.4,
        description: '关键词搜索在混合搜索中的权重（0-1）',
        tooltip: '与语义权重互补，两者之和应为1',
        min: 0,
        max: 1,
        step: 0.1,
        required: true
      },
      min_score: {
        type: 'slider',
        label: '最低相似度阈值',
        default: 0.3,
        description: '过滤掉相似度低于此阈值的结果',
        tooltip: '值越高，结果越精确但可能遗漏相关内容',
        min: 0,
        max: 1,
        step: 0.05,
        required: false
      }
    },
    configTemplates: [
      {
        name: '精确搜索',
        description: '更注重关键词匹配，适合精确查找',
        config: {
          top_k: 5,
          semantic_weight: 0.3,
          keyword_weight: 0.7,
          min_score: 0.5
        }
      },
      {
        name: '语义搜索',
        description: '更注重语义理解，适合概念查找',
        config: {
          top_k: 8,
          semantic_weight: 0.8,
          keyword_weight: 0.2,
          min_score: 0.3
        }
      },
      {
        name: '平衡搜索',
        description: '关键词和语义平衡，适合一般场景',
        config: {
          top_k: 5,
          semantic_weight: 0.5,
          keyword_weight: 0.5,
          min_score: 0.4
        }
      }
    ]
  },

  chat: {
    name: 'Chat Agent',
    icon: MessageOutlined,
    color: '#52c41a',
    description: '对话助手 - 通用的AI对话助手',
    detailedDescription: '基于大语言模型的通用对话助手，能够进行自然语言对话、回答问题、提供建议，适合各种通用任务场景。',
    capabilities: [
      '自然对话',
      '问答系统',
      '任务协助',
      '内容生成',
      '知识问答',
      '多轮对话'
    ],
    usageExample: '用简单的语言解释量子计算的基本原理',
    useCases: [
      '通用问答',
      '知识咨询',
      '任务辅助',
      '创意讨论'
    ],
    configSchema: {
      temperature: {
        type: 'slider',
        label: '创造性程度',
        default: 0.7,
        description: '控制回复的随机性和创造性（0-1）',
        tooltip: '值越高，回复越有创意但可能不够准确；值越低，回复越保守准确',
        min: 0,
        max: 1,
        step: 0.1,
        required: true
      },
      max_tokens: {
        type: 'number',
        label: '最大回复长度',
        default: 1000,
        description: '回复的最大token数量',
        tooltip: '限制AI回复的长度，避免过长的输出',
        min: 100,
        max: 4000,
        required: true
      },
      system_prompt: {
        type: 'textarea',
        label: '系统提示词',
        default: '你是一个智能的AI助手，能够进行自然、有帮助的对话。',
        description: '定义Agent的角色和行为方式',
        tooltip: '系统提示词会影响Agent的回复风格和专业领域',
        placeholder: '输入自定义的系统提示词...',
        required: false
      },
      context_window: {
        type: 'number',
        label: '上下文窗口',
        default: 5,
        description: '保留的历史对话轮数',
        tooltip: '保留更多对话历史可以提供更好的上下文，但会消耗更多token',
        min: 1,
        max: 20,
        required: true
      }
    },
    configTemplates: [
      {
        name: '精确模式',
        description: '更准确但较保守的回复',
        config: {
          temperature: 0.3,
          max_tokens: 800,
          context_window: 5
        }
      },
      {
        name: '创意模式',
        description: '更有创意和发散性的回复',
        config: {
          temperature: 0.9,
          max_tokens: 1500,
          context_window: 3
        }
      },
      {
        name: '平衡模式',
        description: '准确性和创造性平衡',
        config: {
          temperature: 0.7,
          max_tokens: 1000,
          context_window: 5
        }
      }
    ]
  },

  rag: {
    name: 'RAG Agent',
    icon: FileTextOutlined,
    color: '#fa8c16',
    description: 'RAG Agent - 基于文档的问答助手',
    detailedDescription: '检索增强生成（RAG）Agent，结合文档检索和AI生成能力，能够基于上传的文档内容回答问题，提供有依据的答案。',
    capabilities: [
      '文档问答',
      '信息提取',
      '内容总结',
      '引用来源',
      '上下文理解',
      '知识融合'
    ],
    usageExample: '根据上传的文档，总结项目的核心功能',
    useCases: [
      '文档问答',
      '知识提取',
      '内容分析',
      '报告生成'
    ],
    configSchema: {
      top_k: {
        type: 'number',
        label: '检索文档数量',
        default: 3,
        description: '从知识库检索的文档数量',
        tooltip: '检索更多文档可以提供更全面的答案，但可能引入噪音',
        min: 1,
        max: 10,
        required: true
      },
      temperature: {
        type: 'slider',
        label: '生成温度',
        default: 0.3,
        description: '控制答案生成的创造性（0-1）',
        tooltip: 'RAG场景建议使用较低温度，确保答案基于文档内容',
        min: 0,
        max: 1,
        step: 0.1,
        required: true
      },
      max_tokens: {
        type: 'number',
        label: '最大回复长度',
        default: 1500,
        description: '回复的最大token数量',
        tooltip: 'RAG场景可能需要较长的回复来整合多个文档内容',
        min: 500,
        max: 4000,
        required: true
      },
      citation_mode: {
        type: 'select',
        label: '引用模式',
        default: 'inline',
        description: '如何在答案中显示文档来源',
        tooltip: '选择引用来源的显示方式',
        options: [
          { label: '内联引用', value: 'inline' },
          { label: '末尾引用', value: 'footnote' },
          { label: '不显示引用', value: 'none' }
        ],
        required: true
      }
    },
    configTemplates: [
      {
        name: '精确问答',
        description: '严格基于文档内容回答',
        config: {
          top_k: 3,
          temperature: 0.1,
          max_tokens: 1000,
          citation_mode: 'inline'
        }
      },
      {
        name: '综合分析',
        description: '综合多个文档进行分析',
        config: {
          top_k: 5,
          temperature: 0.3,
          max_tokens: 2000,
          citation_mode: 'footnote'
        }
      },
      {
        name: '快速总结',
        description: '快速提取关键信息',
        config: {
          top_k: 2,
          temperature: 0.2,
          max_tokens: 800,
          citation_mode: 'none'
        }
      }
    ]
  },

  data_analyst: {
    name: 'Data Analyst Agent',
    icon: BarChartOutlined,
    color: '#722ed1',
    description: '数据分析师 - 专业的数据分析和可视化专家',
    detailedDescription: '专业的数据分析Agent，擅长数据处理、统计分析、数据可视化建议，能够使用计算器、数据处理器和数据库查询工具。',
    capabilities: [
      '数值计算',
      '统计分析',
      '数据处理',
      '数据库查询',
      '数据探索',
      '可视化建议'
    ],
    usageExample: '计算 15 + 3 * 4，并分析结果',
    useCases: [
      '数据计算',
      '统计分析',
      '数据查询',
      '趋势分析'
    ],
    configSchema: {
      precision: {
        type: 'number',
        label: '计算精度',
        default: 2,
        description: '数值计算结果保留的小数位数',
        tooltip: '设置计算结果的小数精度',
        min: 0,
        max: 10,
        required: true
      },
      auto_visualize: {
        type: 'select',
        label: '自动可视化建议',
        default: 'smart',
        description: '是否自动提供数据可视化建议',
        tooltip: '智能模式会根据数据类型自动建议合适的图表',
        options: [
          { label: '智能模式', value: 'smart' },
          { label: '总是建议', value: 'always' },
          { label: '从不建议', value: 'never' }
        ],
        required: true
      },
      default_db_limit: {
        type: 'number',
        label: '数据库查询默认限制',
        default: 100,
        description: '数据库查询默认返回的最大行数',
        tooltip: '防止查询返回过多数据',
        min: 10,
        max: 1000,
        required: true
      },
      enable_tools: {
        type: 'select',
        label: '启用工具',
        default: 'all',
        description: '选择启用的数据分析工具',
        tooltip: '可以限制Agent使用的工具范围',
        options: [
          { label: '全部工具', value: 'all' },
          { label: '仅计算器', value: 'calculator' },
          { label: '仅数据库', value: 'database' },
          { label: '计算器和数据处理', value: 'calc_process' }
        ],
        required: true
      }
    },
    configTemplates: [
      {
        name: '快速计算',
        description: '用于简单的数值计算',
        config: {
          precision: 2,
          auto_visualize: 'never',
          default_db_limit: 50,
          enable_tools: 'calculator'
        }
      },
      {
        name: '数据分析',
        description: '完整的数据分析能力',
        config: {
          precision: 4,
          auto_visualize: 'smart',
          default_db_limit: 100,
          enable_tools: 'all'
        }
      },
      {
        name: '数据库专用',
        description: '专注于数据库查询和分析',
        config: {
          precision: 2,
          auto_visualize: 'always',
          default_db_limit: 200,
          enable_tools: 'database'
        }
      }
    ]
  }
};

/**
 * 获取Agent类型列表
 */
export const getAgentTypes = (): string[] => {
  return Object.keys(AGENT_TYPE_INFO);
};

/**
 * 获取Agent类型信息
 */
export const getAgentTypeInfo = (type: string): AgentTypeInfo | undefined => {
  return AGENT_TYPE_INFO[type];
};

/**
 * 获取Agent类型名称
 */
export const getAgentTypeName = (type: string): string => {
  return AGENT_TYPE_INFO[type]?.name || type;
};

/**
 * 获取Agent类型颜色
 */
export const getAgentTypeColor = (type: string): string => {
  return AGENT_TYPE_INFO[type]?.color || '#666';
};