"""Evaluation pipeline for comparing multi-step vs oracle baseline"""

from typing import List, Dict
from dataclasses import dataclass
from statistics import mean
from src.models import Task, EpisodeResult, EpisodeStatus, AggregatedResults
from src.curriculum import TaskCurriculum
from src.agent import MultiStepAgent
from src.verifier import Verifier
from src.reward import RewardCalculator
from src.environment import WebEnvironment, ElementNotFoundError, PageTimeoutError


@dataclass
class EvaluationConfig:
    """Configuration for evaluation"""
    difficulties: List[int]
    max_inference_calls_buffer: int = 2
    base_url: str = "http://localhost:3000"


class EvaluationPipeline:
    """Run evaluation comparing multi-step vs oracle baseline"""
    
    def __init__(
        self,
        curriculum: TaskCurriculum,
        agent: MultiStepAgent,
        verifier: Verifier,
        reward_calculator: RewardCalculator,
        config: EvaluationConfig
    ):
        self.curriculum = curriculum
        self.agent = agent
        self.verifier = verifier
        self.reward_calculator = reward_calculator
        self.config = config
    
    def run(self, env: WebEnvironment) -> Dict[int, AggregatedResults]:
        """Run full evaluation across all difficulties"""
        
        all_results: Dict[int, List[EpisodeResult]] = {
            d: [] for d in self.config.difficulties
        }
        
        for difficulty in self.config.difficulties:
            print(f"\n{'='*50}")
            print(f"Evaluating difficulty {difficulty}")
            print(f"{'='*50}")
            
            tasks = self.curriculum.pool.get(difficulty, [])
            
            for i, task in enumerate(tasks):
                print(f"\nTask {i+1}/{len(tasks)}: {task.description[:50]}...")
                
                result = self._run_episode(task, env)
                all_results[difficulty].append(result)
                
                status_icon = "✓" if result.status == EpisodeStatus.SUCCESS else "✗"
                print(f"  {status_icon} Status: {result.status.value}")
                print(f"    Actions: {result.actual_actions}/{result.min_actions}")
                print(f"    Inference calls: {result.actual_inference_calls}/{result.expected_inference_calls}")
                print(f"    Reward: {result.reward:.3f}")
        
        # Aggregate results
        aggregated = {}
        for difficulty, results in all_results.items():
            aggregated[difficulty] = self._aggregate(difficulty, results)
        
        return aggregated
    
    def _run_episode(self, task: Task, env: WebEnvironment) -> EpisodeResult:
        """Run a single episode"""
        
        # Reset agent
        self.agent.reset()
        
        # Calculate max inference calls
        max_calls = task.expected_inference_calls + self.config.max_inference_calls_buffer
        
        # Reset environment
        url = f"{self.config.base_url}/{task.site}/"
        
        try:
            state = env.reset(url)
        except PageTimeoutError as e:
            return EpisodeResult(
                task_id=task.id,
                difficulty=task.min_actions,
                status=EpisodeStatus.SKIPPED,
                actual_actions=0,
                actual_inference_calls=0,
                min_actions=task.min_actions,
                expected_inference_calls=task.expected_inference_calls,
                multi_step_tokens=0,
                single_step_tokens=task.oracle_tokens,
                reward=0.0,
                failure_reason=str(e)
            )
        
        total_actions = 0
        action_history = []
        
        # Run episode
        while self.agent.inference_calls < max_calls:
            # Agent predicts actions
            actions, tokens = self.agent.predict(state, task.description)
            
            if not actions:
                break
            
            # Execute actions
            for action in actions:
                try:
                    state = env.step(action)
                    total_actions += 1
                    action_history.append(action)
                except ElementNotFoundError:
                    # Skip invalid action, continue
                    continue
                except PageTimeoutError:
                    # Page timeout, end episode
                    return EpisodeResult(
                        task_id=task.id,
                        difficulty=task.min_actions,
                        status=EpisodeStatus.FAILURE,
                        actual_actions=total_actions,
                        actual_inference_calls=self.agent.inference_calls,
                        min_actions=task.min_actions,
                        expected_inference_calls=task.expected_inference_calls,
                        multi_step_tokens=self.agent.total_tokens,
                        single_step_tokens=task.oracle_tokens,
                        reward=0.0,
                        failure_reason="Page timeout",
                        action_history=action_history
                    )
            
            # Check success
            if self.verifier.verify(task, state):
                reward = self.reward_calculator.compute(
                    success=True,
                    actual_actions=total_actions,
                    actual_inference_calls=self.agent.inference_calls,
                    min_actions=task.min_actions,
                    expected_inference_calls=task.expected_inference_calls
                )
                
                return EpisodeResult(
                    task_id=task.id,
                    difficulty=task.min_actions,
                    status=EpisodeStatus.SUCCESS,
                    actual_actions=total_actions,
                    actual_inference_calls=self.agent.inference_calls,
                    min_actions=task.min_actions,
                    expected_inference_calls=task.expected_inference_calls,
                    multi_step_tokens=self.agent.total_tokens,
                    single_step_tokens=task.oracle_tokens,
                    reward=reward,
                    action_history=action_history
                )
        
        # Max iterations exceeded
        return EpisodeResult(
            task_id=task.id,
            difficulty=task.min_actions,
            status=EpisodeStatus.FAILURE,
            actual_actions=total_actions,
            actual_inference_calls=self.agent.inference_calls,
            min_actions=task.min_actions,
            expected_inference_calls=task.expected_inference_calls,
            multi_step_tokens=self.agent.total_tokens,
            single_step_tokens=task.oracle_tokens,
            reward=0.0,
            failure_reason="Max iterations exceeded",
            action_history=action_history
        )
    
    def _aggregate(
        self,
        difficulty: int,
        results: List[EpisodeResult]
    ) -> AggregatedResults:
        """Aggregate results for a difficulty level"""
        
        if not results:
            return AggregatedResults(
                difficulty=difficulty,
                num_episodes=0,
                success_rate=0.0,
                avg_actual_actions=0.0,
                avg_min_actions=0.0,
                avg_inference_calls=0.0,
                avg_expected_calls=0.0,
                avg_multi_step_tokens=0.0,
                avg_single_step_tokens=0.0,
                token_reduction_percent=0.0,
                avg_reward=0.0
            )
        
        successes = [r for r in results if r.status == EpisodeStatus.SUCCESS]
        
        avg_multi_tokens = mean(r.multi_step_tokens for r in results)
        avg_single_tokens = mean(r.single_step_tokens for r in results)
        
        token_reduction = 0.0
        if avg_single_tokens > 0:
            token_reduction = (1 - avg_multi_tokens / avg_single_tokens) * 100
        
        return AggregatedResults(
            difficulty=difficulty,
            num_episodes=len(results),
            success_rate=len(successes) / len(results),
            avg_actual_actions=mean(r.actual_actions for r in results),
            avg_min_actions=mean(r.min_actions for r in results),
            avg_inference_calls=mean(r.actual_inference_calls for r in results),
            avg_expected_calls=mean(r.expected_inference_calls for r in results),
            avg_multi_step_tokens=avg_multi_tokens,
            avg_single_step_tokens=avg_single_tokens,
            token_reduction_percent=token_reduction,
            avg_reward=mean(r.reward for r in results)
        )

