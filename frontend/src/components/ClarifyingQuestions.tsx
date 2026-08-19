import { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Textarea } from './ui/textarea';
import { ClarifyingQuestion, QuestionAnswer } from '../types/analysis';

interface ClarifyingQuestionsProps {
  questions: ClarifyingQuestion[];
  onSubmit: (answers: QuestionAnswer[]) => void;
  onSkip: () => void;
  isSubmitting?: boolean;
}

export function ClarifyingQuestions({
  questions,
  onSubmit,
  onSkip,
  isSubmitting = false,
}: ClarifyingQuestionsProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const setAnswer = (id: string, value: string) => {
    setAnswers(prev => ({ ...prev, [id]: value }));
  };

  const handleSubmit = () => {
    const payload: QuestionAnswer[] = questions
      .map(q => ({
        question: q.question,
        answer: (answers[q.id] || '').trim(),
        skill_targeted: q.skill_targeted,
        target_bullet: q.target_bullet,
      }))
      .filter(a => a.answer.length > 0);
    onSubmit(payload);
  };

  const answeredCount = Object.values(answers).filter(v => v.trim().length > 0).length;

  if (questions.length === 0) {
    return (
      <Card style={{ padding: '20px', marginBottom: '20px', backgroundColor: '#e8f5e9' }}>
        <h3 style={{ marginTop: 0, color: '#2e7d32' }}>✅ No clarifications needed</h3>
        <p>Your resume is already clear enough — generating suggestions now.</p>
        <Button onClick={onSkip} disabled={isSubmitting} style={{ marginTop: '10px' }}>
          {isSubmitting ? 'Generating…' : 'Continue'}
        </Button>
      </Card>
    );
  }

  return (
    <div style={{ marginBottom: '20px' }}>
      <Card
        style={{
          padding: '20px',
          marginBottom: '15px',
          backgroundColor: '#e3f2fd',
          borderColor: '#1976d2',
        }}
      >
        <h3 style={{ marginTop: 0, color: '#0d47a1' }}>
          💬 A few quick questions ({questions.length})
        </h3>
        <p style={{ marginBottom: 0, fontSize: '14px' }}>
          Your answers help the AI insert missing skills accurately instead of guessing. Answer as
          many as you'd like — you can skip the rest.
        </p>
      </Card>

      {questions.map((q, idx) => (
        <Card key={q.id} style={{ padding: '20px', marginBottom: '15px' }}>
          <div style={{ marginBottom: '10px' }}>
            <span
              style={{
                backgroundColor: '#1976d2',
                color: 'white',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold',
                marginRight: '8px',
              }}
            >
              Q{idx + 1}
            </span>
            <span style={{ fontSize: '13px', color: '#666' }}>
              Related to: <strong>{q.skill_targeted}</strong>
              {q.target_experience && <> · {q.target_experience}</>}
            </span>
          </div>

          {q.target_bullet && (
            <div
              style={{
                borderLeft: '3px solid #1976d2',
                backgroundColor: '#f5f8fc',
                padding: '8px 12px',
                margin: '10px 0',
                fontSize: '13px',
                color: '#37474f',
              }}
            >
              <div style={{ fontSize: '11px', color: '#7a8a99', marginBottom: '3px' }}>
                If you confirm, this bullet gets rewritten:
              </div>
              <em>{q.target_bullet}</em>
            </div>
          )}

          <h4 style={{ margin: '10px 0 15px 0' }}>{q.question}</h4>

          {q.question_type === 'multiple_choice' && q.choices.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {q.choices.map(choice => {
                const selected = answers[q.id] === choice;
                return (
                  <label
                    key={choice}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 12px',
                      border: `1px solid ${selected ? '#1976d2' : '#e0e0e0'}`,
                      backgroundColor: selected ? '#e3f2fd' : '#fff',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px',
                    }}
                  >
                    <input
                      type="radio"
                      name={q.id}
                      value={choice}
                      checked={selected}
                      onChange={() => setAnswer(q.id, choice)}
                    />
                    {choice}
                  </label>
                );
              })}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: '#666',
                }}
              >
                <input
                  type="radio"
                  name={q.id}
                  checked={!q.choices.includes(answers[q.id] || '') && (answers[q.id] || '') === ''}
                  onChange={() => setAnswer(q.id, '')}
                />
                Skip this question
              </label>
            </div>
          ) : (
            <Textarea
              placeholder="Type your answer here (leave blank to skip)…"
              value={answers[q.id] || ''}
              onChange={e => setAnswer(q.id, e.target.value)}
              style={{ width: '100%', minHeight: '70px' }}
            />
          )}
        </Card>
      ))}

      <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          style={{ flex: 1, backgroundColor: '#1976d2', color: 'white' }}
        >
          {isSubmitting
            ? 'Generating suggestions…'
            : `Submit ${answeredCount} answer${answeredCount === 1 ? '' : 's'} & continue`}
        </Button>
        <Button onClick={onSkip} disabled={isSubmitting} variant="outline" style={{ flex: 1 }}>
          Skip all questions
        </Button>
      </div>
    </div>
  );
}
