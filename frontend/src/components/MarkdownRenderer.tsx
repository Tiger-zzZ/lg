import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MarkdownRenderer.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className }) => {
  return (
    <div className={`markdown-renderer ${className || ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 自定义代码块渲染
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <pre className={`code-block language-${match[1]}`}>
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            ) : (
              <code className={`inline-code ${className || ''}`} {...props}>
                {children}
              </code>
            );
          },
          // 自定义表格渲染
          table: ({ children, ...props }) => (
            <div className="table-wrapper">
              <table className="markdown-table" {...props}>
                {children}
              </table>
            </div>
          ),
          // 自定义链接渲染
          a: ({ children, href, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="markdown-link"
              {...props}
            >
              {children}
            </a>
          ),
          // 自定义引用块渲染
          blockquote: ({ children, ...props }) => (
            <blockquote className="markdown-blockquote" {...props}>
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;