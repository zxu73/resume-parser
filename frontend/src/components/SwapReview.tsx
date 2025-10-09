import { Button } from './ui/button';
import { Card } from './ui/card';

interface SwapComparison {
  resume_experience_index: number;
  resume_experience_title: string;
  should_replace: boolean;
  pool_experience_index?: number;
  replacement_reason: string;
  relevance_score_resume: number;
  relevance_score_pool: number;
}

interface SwapReviewProps {
  comparisons: SwapComparison[];
  poolExperiences: any[];
  onAcceptAll: () => void;
  onReject: () => void;
}

export function SwapReview({ comparisons, poolExperiences, onAcceptAll, onReject }: SwapReviewProps) {
  const swapsToApply = comparisons.filter(c => c.should_replace);

  if (swapsToApply.length === 0) {
    return (
      <Card style={{ padding: '20px', marginBottom: '20px', backgroundColor: '#e8f5e9' }}>
        <h3 style={{ marginTop: 0, color: '#2e7d32' }}>✅ No Swaps Needed</h3>
        <p>Your current resume experiences are already well-aligned with the job!</p>
        <p style={{ fontSize: '14px', color: '#666' }}>
          The AI analyzed your pool experiences but found that your existing experiences are the best fit.
        </p>
        <Button onClick={onReject} style={{ marginTop: '10px' }}>
          Continue with Current Resume
        </Button>
      </Card>
    );
  }

  return (
    <div style={{ marginBottom: '20px' }}>
      <Card style={{ padding: '20px', marginBottom: '15px', backgroundColor: '#fff3cd', borderColor: '#ffc107' }}>
        <h3 style={{ marginTop: 0, color: '#856404' }}>
          🔄 {swapsToApply.length} Experience Swap{swapsToApply.length > 1 ? 's' : ''} Recommended
        </h3>
        <p style={{ marginBottom: 0, fontSize: '14px' }}>
          Review the recommendations below. The AI will replace experiences only if you approve.
        </p>
      </Card>

      {swapsToApply.map((comparison, idx) => {
        const poolExp = poolExperiences[comparison.pool_experience_index || 0];
        
        return (
          <Card key={idx} style={{ padding: '20px', marginBottom: '15px' }}>
            <div style={{ marginBottom: '15px' }}>
              <span style={{ 
                backgroundColor: '#f44336', 
                color: 'white', 
                padding: '4px 8px', 
                borderRadius: '4px', 
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                REPLACE
              </span>
            </div>

            {/* Current Experience (will be removed) */}
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ 
                margin: '0 0 10px 0', 
                color: '#d32f2f',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <span>❌ Current (Score: {comparison.relevance_score_resume}/100)</span>
              </h4>
              <div style={{ 
                padding: '15px', 
                backgroundColor: '#ffebee', 
                borderRadius: '8px',
                borderLeft: '4px solid #d32f2f'
              }}>
                <h5 style={{ margin: '0 0 5px 0' }}>{comparison.resume_experience_title}</h5>
                <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
                  Resume Experience #{comparison.resume_experience_index + 1}
                </p>
              </div>
            </div>

            {/* Arrow */}
            <div style={{ textAlign: 'center', margin: '15px 0', fontSize: '24px' }}>
              ⬇️
            </div>

            {/* New Experience (from pool) */}
            <div style={{ marginBottom: '15px' }}>
              <h4 style={{ 
                margin: '0 0 10px 0', 
                color: '#2e7d32',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <span>✅ Better Match (Score: {comparison.relevance_score_pool}/100)</span>
              </h4>
              <div style={{ 
                padding: '15px', 
                backgroundColor: '#e8f5e9', 
                borderRadius: '8px',
                borderLeft: '4px solid #2e7d32'
              }}>
                <h5 style={{ margin: '0 0 5px 0' }}>{poolExp?.title}</h5>
                <p style={{ margin: '5px 0', color: '#666', fontSize: '14px' }}>
                  {poolExp?.company} {poolExp?.duration && `• ${poolExp.duration}`}
                </p>
                <p style={{ margin: '10px 0 0 0', fontSize: '14px' }}>{poolExp?.description}</p>
                {poolExp?.skills && poolExp.skills.length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    {poolExp.skills.map((skill: string, i: number) => (
                      <span 
                        key={i}
                        style={{
                          display: 'inline-block',
                          backgroundColor: '#2196F3',
                          color: 'white',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          marginRight: '5px',
                          marginTop: '5px',
                          fontSize: '12px'
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Reason */}
            <div style={{ 
              padding: '12px', 
              backgroundColor: '#f5f5f5', 
              borderRadius: '8px',
              marginTop: '15px'
            }}>
              <strong style={{ fontSize: '14px' }}>Why this swap?</strong>
              <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#666' }}>
                {comparison.replacement_reason}
              </p>
              <p style={{ margin: '10px 0 0 0', fontSize: '13px', fontWeight: 'bold', color: '#2e7d32' }}>
                +{Math.round(comparison.relevance_score_pool - comparison.relevance_score_resume)} points improvement
              </p>
            </div>
          </Card>
        );
      })}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
        <Button onClick={onAcceptAll} style={{ flex: 1, backgroundColor: '#2e7d32', color: 'white' }}>
          ✅ Accept All Swaps & Improve Resume
        </Button>
        <Button onClick={onReject} variant="outline" style={{ flex: 1 }}>
          ❌ Reject & Keep Current Resume
        </Button>
      </div>
    </div>
  );
}
