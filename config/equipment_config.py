"""
Equipment Configuration
장비 옵션 설정 모듈

이 모듈은 AFM 장비의 타입별 선택 옵션을 정의하고,
각 옵션을 평탄화하여 반환하는 헬퍼 함수들을 제공합니다.
"""

# Equipment Options (From Tkinter App)
EQUIPMENT_OPTIONS = {
    'xy_scanner': {
        'Single': ['10µm', '100µm', '150µm'],
        'Dual': ['Dual 10µm(50µm)', 'Dual 100µm(10µm)', 'Dual 100µm(150µm)', 'Dual 100µm(300mm)']
    },
    'head_type': {
        'Standard': ['Standard', 'Auto Align Standard'],
        'Long': ['Long', 'Auto Align Long'],
        'FX': ['FX Standard'],
        'NX-Hivac': ['NX-Hivac Auto Align'],
        'TSH': ['TSH 50µm', 'TSH 100µm']
    },
    'mod_vit': {
        'N/A': ['N/A'],
        'Accurion': ['Accurion i4', 'Accurion i4 medium', 'Accurion Nano30', 'Accurion Vario(6units)', 'Accurion Vario(8units)'],
        'Dual MOD': ['Dual MOD 4 units', 'Dual MOD 6 units', 'Dual MOD 7 units', 'Dual MOD 8 units'],
        'Single MOD': ['Single MOD 2 units', 'Single MOD 6 units'],
        'Mini450F': ['Mini450F'],
        'Minus-K': ['Minus-K']
    },
    'sliding_stage': {
        'None': ['N/A'],
        'Stage': ['10mm', '50mm']
    },
    'sample_chuck': {
        'N/A': ['N/A'],
        'AL': ['AL Bar type chuck'],
        'SiC': ['SiC Anti-warpage chuck', 'SiC Bar type chuck', 'SiC Flat type chuck', 
                'SiC Fork type chuck', 'SiC Pin Bar type chuck'],
        'Vacuum': ['Vacuum Sample Chuck'],
        'Mask': ['Mask'],
        'Coreflow': ['Coreflow customized']
    },
    'ae': {
        'Research': ['N/A', 'AE101', 'AE201', 'AE202', 'AE203', 'AE204', 'AE401', 'AE402', 
                     'FX200 AE', 'FX40 AE', 'Glove Box', 'Chamber'],
        'Industrial': ['N/A', 'Double Walled', 'Isolated']
    }
}


# Helper functions to get flattened options for SelectboxColumn
def get_xy_scanner_options():
    """Get all XY Scanner options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['xy_scanner'].items():
        options.extend(values)
    return options

def get_head_type_options():
    """Get all Head Type options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['head_type'].items():
        options.extend(values)
    return options

def get_mod_vit_options():
    """Get all MOD/VIT options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['mod_vit'].items():
        options.extend(values)
    return options

def get_sliding_stage_options():
    """Get all Sliding Stage options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['sliding_stage'].items():
        options.extend(values)
    return options

def get_sample_chuck_options():
    """Get all Sample Chuck options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['sample_chuck'].items():
        options.extend(values)
    return options

def get_ae_options():
    """Get all AE options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['ae'].items():
        options.extend(values)
    return options
