import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card } from './ui/card';

export interface Experience {
  id: string;
  title: string;
  company: string;
  duration: string;
  description: string;
  skills: string[];
}

interface ExperienceManagerProps {
  experiences: Experience[];
  onExperiencesChange: (experiences: Experience[]) => void;
}

export function ExperienceManager({ experiences, onExperiencesChange }: ExperienceManagerProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [currentExperience, setCurrentExperience] = useState<Partial<Experience>>({
    title: '',
    company: '',
    duration: '',
    description: '',
    skills: []
  });
  const [skillInput, setSkillInput] = useState('');

  const handleAddExperience = () => {
    if (!currentExperience.title || !currentExperience.company || !currentExperience.description) {
      alert('Please fill in Job Title, Company, and Description');
      return;
    }

    const newExperience: Experience = {
      id: Date.now().toString(),
      title: currentExperience.title || '',
      company: currentExperience.company || '',
      duration: currentExperience.duration || '',
      description: currentExperience.description || '',
      skills: currentExperience.skills || []
    };

    onExperiencesChange([...experiences, newExperience]);
    
    // Reset form
    setCurrentExperience({
      title: '',
      company: '',
      duration: '',
      description: '',
      skills: []
    });
    setSkillInput('');
    setIsAdding(false);
  };

  const handleRemoveExperience = (id: string) => {
    onExperiencesChange(experiences.filter(exp => exp.id !== id));
  };

  const handleAddSkill = () => {
    if (skillInput.trim()) {
      setCurrentExperience({
        ...currentExperience,
        skills: [...(currentExperience.skills || []), skillInput.trim()]
      });
      setSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setCurrentExperience({
      ...currentExperience,
      skills: (currentExperience.skills || []).filter(skill => skill !== skillToRemove)
    });
  };

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h2>Your Experience Pool</h2>
        {!isAdding && (
          <Button onClick={() => setIsAdding(true)}>
            + Add Experience
          </Button>
        )}
      </div>

      <p style={{ marginBottom: '15px', color: '#666', fontSize: '14px' }}>
        Add all your work experiences here. The AI will select the best ones for your target job and ensure your resume fits on 1 page.
      </p>

      {/* List of added experiences */}
      {experiences.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          {experiences.map((exp) => (
            <Card key={exp.id} style={{ padding: '15px', marginBottom: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: 0, marginBottom: '5px' }}>{exp.title}</h3>
                  <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>
                    {exp.company} {exp.duration && `• ${exp.duration}`}
                  </p>
                  <p style={{ margin: '10px 0', fontSize: '14px' }}>{exp.description}</p>
                  {exp.skills.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      {exp.skills.map((skill, idx) => (
                        <span 
                          key={idx}
                          style={{
                            display: 'inline-block',
                            backgroundColor: '#e3f2fd',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            marginRight: '5px',
                            marginBottom: '5px',
                            fontSize: '12px'
                          }}
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <Button 
                  variant="outline" 
                  onClick={() => handleRemoveExperience(exp.id)}
                  style={{ marginLeft: '10px' }}
                >
                  Remove
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Add new experience form */}
      {isAdding && (
        <Card style={{ padding: '20px', marginBottom: '20px', backgroundColor: '#f5f5f5' }}>
          <h3 style={{ marginTop: 0 }}>Add New Experience</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Job Title *
            </label>
            <Input
              placeholder="e.g., Software Engineer"
              value={currentExperience.title || ''}
              onChange={(e) => setCurrentExperience({ ...currentExperience, title: e.target.value })}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Company *
            </label>
            <Input
              placeholder="e.g., Google"
              value={currentExperience.company || ''}
              onChange={(e) => setCurrentExperience({ ...currentExperience, company: e.target.value })}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Duration
            </label>
            <Input
              placeholder="e.g., Jan 2020 - Dec 2022"
              value={currentExperience.duration || ''}
              onChange={(e) => setCurrentExperience({ ...currentExperience, duration: e.target.value })}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Description *
            </label>
            <Textarea
              placeholder="Describe your role, responsibilities, and achievements..."
              value={currentExperience.description || ''}
              onChange={(e) => setCurrentExperience({ ...currentExperience, description: e.target.value })}
              style={{ minHeight: '100px' }}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Skills Used
            </label>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
              <Input
                placeholder="e.g., Python"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddSkill()}
              />
              <Button onClick={handleAddSkill} type="button">
                Add Skill
              </Button>
            </div>
            {currentExperience.skills && currentExperience.skills.length > 0 && (
              <div>
                {currentExperience.skills.map((skill, idx) => (
                  <span 
                    key={idx}
                    style={{
                      display: 'inline-block',
                      backgroundColor: '#2196F3',
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      marginRight: '5px',
                      marginBottom: '5px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                    onClick={() => handleRemoveSkill(skill)}
                  >
                    {skill} ×
                  </span>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <Button onClick={handleAddExperience}>
              Save Experience
            </Button>
            <Button 
              variant="outline" 
              onClick={() => {
                setIsAdding(false);
                setCurrentExperience({
                  title: '',
                  company: '',
                  duration: '',
                  description: '',
                  skills: []
                });
                setSkillInput('');
              }}
            >
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {experiences.length === 0 && !isAdding && (
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          backgroundColor: '#f5f5f5', 
          borderRadius: '8px',
          color: '#666'
        }}>
          <p>No experiences added yet.</p>
          <p style={{ fontSize: '14px' }}>Click "Add Experience" to start building your experience pool.</p>
        </div>
      )}
    </div>
  );
}
