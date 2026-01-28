"""
Equipment Configuration Validator
장비 구성 검증 엔진 - JSON 규칙 기반
"""

import json
import os
from typing import Dict, List, Optional, Tuple


class EquipmentConfigValidator:
    """장비 구성 검증 클래스"""
    
    def __init__(self, rules_file='equipment_config_rules.json'):
        """
        초기화
        
        Args:
            rules_file: 규칙 JSON 파일 경로
        """
        # 현재 파일과 같은 디렉토리에서 규칙 파일 찾기
        if not os.path.isabs(rules_file):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rules_file = os.path.join(current_dir, rules_file)
        
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"규칙 파일을 찾을 수 없습니다: {rules_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"규칙 파일 JSON 파싱 오류: {e}")
    
    def get_model_info(self, model: str) -> Optional[Dict]:
        """
        모델 정보 조회
        
        Args:
            model: 모델명
            
        Returns:
            모델 규칙 딕셔너리 또는 None
        """
        return self.rules.get('model_specific_rules', {}).get(model)
    
    def get_model_category(self, model: str) -> str:
        """
        모델 카테고리 반환 (industrial/research)
        
        Args:
            model: 모델명
            
        Returns:
            'industrial', 'research', 또는 'unknown'
        """
        model_info = self.get_model_info(model)
        if model_info:
            return model_info.get('category', 'unknown')
        
        # 카테고리 목록에서 찾기
        for category, models in self.rules.get('model_categories', {}).items():
            if model in models:
                return category
        
        return 'unknown'
    
    def get_model_display_name(self, model: str) -> str:
        """
        모델 표시명 반환
        
        Args:
            model: 모델명
            
        Returns:
            표시명 (예: "NX-Wafer (산업용)")
        """
        model_info = self.get_model_info(model)
        if model_info and 'display_name' in model_info:
            return model_info['display_name']
        
        category = self.get_model_category(model)
        if category == 'industrial':
            return f"{model} (산업용)"
        elif category == 'research':
            return f"{model} (연구용)"
        else:
            return model
    
    def get_allowed_options(self, model: str, field: str, 
                           current_config: Optional[Dict[str, str]] = None) -> List[str]:
        """
        허용된 옵션 목록 반환 (조건부 규칙 적용)
        
        Args:
            model: 모델명
            field: 필드명
            current_config: 현재 선택된 구성
            
        Returns:
            허용된 옵션 리스트
        """
        model_info = self.get_model_info(model)
        if not model_info:
            return []
        
        field_info = model_info.get(field, {})
        allowed = field_info.get('allowed', [])
        
        # 조건부 규칙 적용
        if current_config:
            allowed = self._apply_conditional_rules(
                field, allowed, current_config
            )
        
        return allowed
    
    def is_field_required(self, model: str, field: str) -> bool:
        """
        필드가 필수인지 확인
        
        Args:
            model: 모델명
            field: 필드명
            
        Returns:
            필수 여부
        """
        model_info = self.get_model_info(model)
        if not model_info:
            return False
        
        field_info = model_info.get(field, {})
        return field_info.get('required', False)
    
    def get_required_fields(self, model: str) -> List[str]:
        """
        필수 필드 목록 반환
        
        Args:
            model: 모델명
            
        Returns:
            필수 필드명 리스트
        """
        model_info = self.get_model_info(model)
        if not model_info:
            return []
        
        required = []
        for field, info in model_info.items():
            if isinstance(info, dict) and info.get('required', False):
                required.append(field)
        
        return required
    
    def get_default_config(self, model: str) -> Dict[str, str]:
        """
        모델의 기본 구성 반환
        
        Args:
            model: 모델명
            
        Returns:
            기본 구성 딕셔너리
        """
        defaults = self.rules.get('default_selections', {})
        return defaults.get(model, {})
    
    def validate_config(self, model: str, config: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        전체 구성 검증
        
        Args:
            model: 모델명
            config: 선택된 구성 딕셔너리
            
        Returns:
            (검증 성공 여부, 오류 메시지 리스트)
        """
        errors = []
        model_info = self.get_model_info(model)
        
        if not model_info:
            errors.append(f"알 수 없는 모델: {model}")
            return False, errors
        
        # 1. 필수 필드 확인
        for field in self.get_required_fields(model):
            if not config.get(field):
                field_display = self.rules.get('field_display_names', {}).get(field, field)
                errors.append(f"필수 필드 누락: {field_display}")
        
        # 2. 허용 옵션 확인
        for field, value in config.items():
            if value:
                field_info = model_info.get(field, {})
                allowed = field_info.get('allowed', [])
                
                if allowed and value not in allowed:
                    field_display = self.rules.get('field_display_names', {}).get(field, field)
                    errors.append(
                        f"{field_display}: '{value}'는 {model}에서 사용할 수 없습니다"
                    )
        
        # 3. 조건부 규칙 검증
        conditional_errors = self._validate_conditional_rules(config)
        errors.extend(conditional_errors)
        
        return len(errors) == 0, errors
    
    def _apply_conditional_rules(self, target_field: str, 
                                 allowed_options: List[str],
                                 current_config: Dict[str, str]) -> List[str]:
        """
        조건부 규칙을 적용하여 옵션 필터링
        
        Args:
            target_field: 대상 필드
            allowed_options: 허용된 옵션 리스트
            current_config: 현재 구성
            
        Returns:
            필터링된 옵션 리스트
        """
        filtered = allowed_options.copy()
        
        for rule in self.rules.get('conditional_rules', []):
            enforce = rule.get('enforce', {})
            
            # 이 규칙이 target_field에 적용되는가?
            if enforce.get('field') != target_field:
                continue
            
            # 조건 확인
            if self._check_condition(rule.get('condition', {}), current_config):
                # 조건부 강제 적용
                operator = enforce.get('operator')
                
                if operator == 'must_contain':
                    value = enforce.get('value')
                    filtered = [opt for opt in filtered if value in opt]
                
                elif operator == 'must_be_one_of':
                    values = enforce.get('values', [])
                    filtered = [opt for opt in filtered if opt in values]
        
        return filtered
    
    def _check_condition(self, condition: Dict, config: Dict[str, str]) -> bool:
        """
        조건 확인
        
        Args:
            condition: 조건 딕셔너리
            config: 현재 구성
            
        Returns:
            조건 만족 여부
        """
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        config_value = config.get(field, '')
        
        if not config_value:
            return False
        
        if operator == 'contains':
            return value in config_value
        elif operator == 'equals':
            return config_value == value
        elif operator == 'not_equals':
            return config_value != value
        
        return False
    
    def _validate_conditional_rules(self, config: Dict[str, str]) -> List[str]:
        """
        조건부 규칙 검증
        
        Args:
            config: 현재 구성
            
        Returns:
            오류 메시지 리스트
        """
        errors = []
        
        for rule in self.rules.get('conditional_rules', []):
            # 조건 확인
            if self._check_condition(rule.get('condition', {}), config):
                # 강제 조건 검증
                enforce = rule.get('enforce', {})
                field = enforce.get('field')
                operator = enforce.get('operator')
                config_value = config.get(field, '')
                
                is_valid = False
                
                if operator == 'must_contain':
                    value = enforce.get('value')
                    is_valid = value in config_value if config_value else False
                
                elif operator == 'must_be_one_of':
                    values = enforce.get('values', [])
                    is_valid = config_value in values if config_value else False
                
                if not is_valid:
                    error_msg = rule.get('error_message', rule.get('description', ''))
                    errors.append(error_msg)
        
        return errors


# 테스트 코드
if __name__ == "__main__":
    validator = EquipmentConfigValidator()
    
    # 테스트 1: NX-Wafer 기본 정보
    print("=== 테스트 1: NX-Wafer 모델 정보 ===")
    print(f"카테고리: {validator.get_model_category('NX-Wafer')}")
    print(f"표시명: {validator.get_model_display_name('NX-Wafer')}")
    print(f"필수 필드: {validator.get_required_fields('NX-Wafer')}")
    print(f"기본 구성: {validator.get_default_config('NX-Wafer')}")
    print()
    
    # 테스트 2: 허용 옵션 조회
    print("=== 테스트 2: 허용 옵션 ===")
    print(f"xy_scanner: {validator.get_allowed_options('NX-Wafer', 'xy_scanner')}")
    print(f"mod_vit: {validator.get_allowed_options('NX-Wafer', 'mod_vit')}")
    print()
    
    # 테스트 3: 조건부 필터링
    print("=== 테스트 3: 조건부 필터링 ===")
    config_dual = {'xy_scanner': 'Dual 100µm(300mm)'}
    print(f"Dual Scanner 선택 시 MOD 옵션: {validator.get_allowed_options('NX-Wafer', 'mod_vit', config_dual)}")
    print()
    
    # 테스트 4: 구성 검증
    print("=== 테스트 4: 구성 검증 ===")
    
    # 올바른 구성
    good_config = {
        'ri': 'Industrial',
        'xy_scanner': 'Dual 100µm(300mm)',
        'head_type': 'Auto Align Standard',
        'mod_vit': 'Dual MOD 6 units',
        'sliding_stage': '10mm'
    }
    is_valid, errors = validator.validate_config('NX-Wafer', good_config)
    print(f"올바른 구성: {is_valid}")
    
    # 잘못된 구성 (Dual Scanner + Single MOD)
    bad_config = {
        'ri': 'Industrial',
        'xy_scanner': 'Dual 100µm(300mm)',
        'head_type': 'Auto Align Standard',
        'mod_vit': 'Single MOD 4 units',
        'sliding_stage': '10mm'
    }
    is_valid, errors = validator.validate_config('NX-Wafer', bad_config)
    print(f"잘못된 구성: {is_valid}")
    print(f"오류: {errors}")
