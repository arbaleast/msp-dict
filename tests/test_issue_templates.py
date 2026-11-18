"""Issue 模板契约测试。

模板是用户提交 Issue 的唯一入口，一旦写坏（YAML 语法错、必填项丢失、
校验命令写错），用户就会在提 Issue 的第一步就被卡住，而且很难自查。
这里把模板当成代码来守护。
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip('yaml', reason='需要 pyyaml 才能解析 Issue 模板')

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / '.github' / 'ISSUE_TEMPLATE'

VALIDATE_CMD = 'python -m src.cli validate'
CHECK_CANARY_CMD = 'python -m src.cli check-canary'

# GitHub Issue Forms 支持的字段类型里，只有这几种能声明 validations.required
REQUIRED_CAPABLE = {'input', 'textarea', 'dropdown'}


def load(name):
    path = TEMPLATE_DIR / name
    assert path.exists(), f'缺少 Issue 模板: {path}'
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def body_items(form):
    body = form.get('body')
    assert isinstance(body, list) and body, 'Issue Form 必须有 body 列表'
    return body


def required_ids(form):
    ids = []
    for item in body_items(form):
        validations = item.get('validations') or {}
        if validations.get('required') is True:
            ids.append(item.get('id'))
    return ids


def item_by_id(form, field_id):
    for item in body_items(form):
        if item.get('id') == field_id:
            return item
    return None


class TestTemplateFiles:
    def test_all_expected_files_exist(self):
        for name in ('bug_report.yml', 'data_source.yml', 'feature_request.yml', 'config.yml'):
            assert (TEMPLATE_DIR / name).exists(), f'缺少 {name}'

    def test_templates_parse_as_yaml(self):
        for name in ('bug_report.yml', 'data_source.yml', 'feature_request.yml', 'config.yml'):
            data = load(name)
            assert isinstance(data, dict), f'{name} 顶层必须是映射'

    def test_form_templates_have_required_metadata(self):
        for name in ('bug_report.yml', 'data_source.yml', 'feature_request.yml'):
            form = load(name)
            assert form.get('name'), f'{name} 缺少 name'
            assert form.get('description'), f'{name} 缺少 description'
            assert isinstance(form.get('body'), list)


class TestIssueFormSchema:
    @pytest.mark.parametrize('name', ['bug_report.yml', 'data_source.yml', 'feature_request.yml'])
    def test_field_ids_are_unique_and_usable(self, name):
        form = load(name)
        ids = []
        for item in body_items(form):
            field_type = item.get('type')
            assert field_type, f'{name} 有字段缺少 type'
            if field_type == 'markdown':
                continue
            field_id = item.get('id')
            assert field_id, f'{name} 字段缺少 id'
            assert field_id.replace('-', '').replace('_', '').isalnum(), \
                f'{name} 的 id 只能包含字母数字和 -_：{field_id}'
            ids.append(field_id)
        assert len(ids) == len(set(ids)), f'{name} 存在重复 id'

    @pytest.mark.parametrize('name', ['bug_report.yml', 'data_source.yml', 'feature_request.yml'])
    def test_required_fields_are_validatable_types(self, name):
        form = load(name)
        for item in body_items(form):
            validations = item.get('validations') or {}
            if validations.get('required') is True:
                assert item.get('type') in REQUIRED_CAPABLE, \
                    f'{name} 的 {item.get("id")} 用了不能声明 required 的类型 {item.get("type")}'

    @pytest.mark.parametrize('name', ['bug_report.yml', 'data_source.yml', 'feature_request.yml'])
    def test_dropdowns_have_options(self, name):
        form = load(name)
        for item in body_items(form):
            if item.get('type') == 'dropdown':
                options = (item.get('attributes') or {}).get('options')
                assert isinstance(options, list) and options, \
                    f'{name} 的下拉 {item.get("id")} 没有可选项'

    @pytest.mark.parametrize('name', ['bug_report.yml', 'data_source.yml', 'feature_request.yml'])
    def test_every_template_requires_reproducible_evidence(self, name):
        form = load(name)
        assert required_ids(form), f'{name} 至少要有一个必填字段'
        text = (TEMPLATE_DIR / name).read_text(encoding='utf-8')
        assert VALIDATE_CMD in text, f'{name} 必须直接引用项目的 validate 命令，不能只让用户描述问题'


class TestBugReport:
    def test_required_fields_are_the_expected_set(self):
        form = load('bug_report.yml')
        required = set(required_ids(form))
        for field_id in ('edition', 'validate_output', 'steps', 'os_version', 'msp_version'):
            assert field_id in required, f'bug_report.yml 的 {field_id} 必须是必填'

    def test_edition_is_a_dropdown_with_real_releases(self):
        form = load('bug_report.yml')
        item = item_by_id(form, 'edition')
        assert item['type'] == 'dropdown'
        options = ' '.join(item['attributes']['options'])
        for edition in ('msp_lite.dat', 'msp_standard.dat', 'msp_full.dat', 'msp_win10.dat'):
            assert edition in options, f'档位下拉缺少 {edition}'

    def test_validate_output_references_the_real_command(self):
        form = load('bug_report.yml')
        item = item_by_id(form, 'validate_output')
        assert item['type'] == 'textarea'
        assert VALIDATE_CMD in item['attributes']['description']

    def test_canary_command_is_mentioned(self):
        text = (TEMPLATE_DIR / 'bug_report.yml').read_text(encoding='utf-8')
        assert CHECK_CANARY_CMD in text


class TestDataSource:
    def test_required_fields_are_the_expected_set(self):
        form = load('data_source.yml')
        required = set(required_ids(form))
        for field_id in ('source_file', 'expected_direction', 'validate_output'):
            assert field_id in required, f'data_source.yml 的 {field_id} 必须是必填'

    def test_expected_direction_is_a_dropdown(self):
        form = load('data_source.yml')
        item = item_by_id(form, 'expected_direction')
        assert item['type'] == 'dropdown'
        assert len(item['attributes']['options']) >= 3

    def test_source_file_examples_are_real_cached_names(self):
        form = load('data_source.yml')
        item = item_by_id(form, 'source_file')
        description = item['attributes']['description']
        for real in ('rime-ice_base.txt', 'rime-frost_food.txt', 'ext-moegirl.dict.yaml',
                     'ext-zhwiki.dict.yaml'):
            assert real in description, f'数据源字段应举例真实缓存文件名 {real}'

    def test_validate_output_references_the_real_command(self):
        form = load('data_source.yml')
        item = item_by_id(form, 'validate_output')
        assert VALIDATE_CMD in item['attributes']['description']


class TestFeatureRequest:
    def test_requires_problem_and_evidence(self):
        form = load('feature_request.yml')
        required = set(required_ids(form))
        assert 'problem' in required
        assert 'current_behavior' in required

    def test_evidence_field_references_the_real_command(self):
        form = load('feature_request.yml')
        item = item_by_id(form, 'current_behavior')
        assert VALIDATE_CMD in item['attributes']['description']


class TestConfig:
    def test_blank_issues_disabled(self):
        config = load('config.yml')
        assert config.get('blank_issues_enabled') is False, \
            '空白 Issue 必须关闭，否则模板形同虚设'

    def test_contact_links_point_at_existing_docs(self):
        config = load('config.yml')
        links = config.get('contact_links') or []
        assert links, 'config.yml 应至少给出一个引导链接'
        for link in links:
            assert link.get('url') and link.get('about')
            assert link['url'].startswith('https://github.com/arbaleast/msp-dict/')

    def test_discussions_is_referenced(self):
        text = (TEMPLATE_DIR / 'config.yml').read_text(encoding='utf-8')
        assert 'discussions' in text, '一般使用问题应引导到 Discussions'
