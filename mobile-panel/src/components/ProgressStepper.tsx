// Progress stepper component for showing draft flow stages

interface ProgressStepperProps {
  currentStep: number;
  steps: string[];
}

export function ProgressStepper({ currentStep, steps }: ProgressStepperProps) {
  return (
    <section className="stepper-card">
      {steps.map((label, idx) => {
        const number = idx + 1;
        const active = currentStep >= number;
        return (
          <div key={label} className={`step ${active ? "active" : ""}`}>
            <span>{number}</span>
            <small>{label}</small>
          </div>
        );
      })}
    </section>
  );
}
