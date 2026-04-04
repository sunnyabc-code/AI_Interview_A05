from django.db.models import Avg
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.response import APIResponse
from recommendations.models import UserKnowledgeMatrics
from positions.models import JobPosition


def _safe_float(value):
	if value is None:
		return 0.0
	return float(value)


class KnowledgeFeedbackView(APIView):
	permission_classes = [IsAuthenticated]

	@swagger_auto_schema(
		tags=['Recommendation'],
		operation_summary='知识点掌握反馈',
		operation_description='按岗位分组返回该用户已测试知识点的次数与 logic/accuracy 平均分。',
		security=[{'Bearer': []}],
		responses={
			200: openapi.Response('获取成功'),
			401: openapi.Response('未登录'),
		},
	)
	def get(self, request):
		queryset = UserKnowledgeMatrics.objects.select_related(
			'interview',
			'job_knowledge',
		).filter(interview__user=request.user)

		records = list(queryset.order_by('-id'))
		if not records:
			return APIResponse.success(
				data={
					'positions': [],
				},
				message='暂无知识点评分数据',
				code=200,
			)

		position_ids = {
			row.job_knowledge.job_id
			for row in records
			if row.job_knowledge and row.job_knowledge.job_id
		}
		position_map = {
			item['id']: item['name']
			for item in JobPosition.objects.filter(id__in=position_ids).values('id', 'name')
		}

		aggregated = {}
		for row in records:
			key = row.job_knowledge_id
			position_id = row.job_knowledge.job_id
			position_name = position_map.get(position_id, '未知岗位')
			item = aggregated.setdefault(
				key,
				{
					'knowledge_id': row.job_knowledge_id,
					'knowledge_name': row.job_knowledge.name,
					'position_id': position_id,
					'position_name': position_name,
					'attempt_count': 0,
					'logic_sum': 0,
					'accuracy_sum': 0,
				},
			)
			item['attempt_count'] += 1
			item['logic_sum'] += row.logic
			item['accuracy_sum'] += row.accuracy

		position_group_map = {}
		for point in aggregated.values():
			logic_avg = round(point['logic_sum'] / point['attempt_count'], 2)
			accuracy_avg = round(point['accuracy_sum'] / point['attempt_count'], 2)
			group = position_group_map.setdefault(
				point['position_id'],
				{
					'position_name': point['position_name'],
					'knowledge_points': [],
				},
			)
			group['knowledge_points'].append(
				{
					'knowledge_id': point['knowledge_id'],
					'knowledge_name': point['knowledge_name'],
					'test_count': point['attempt_count'],
					'avg_logic': logic_avg,
					'avg_accuracy': accuracy_avg,
				}
			)

		positions = list(position_group_map.values())
		for position in positions:
			position['knowledge_points'].sort(
				key=lambda item: (item['avg_logic'] + item['avg_accuracy'], item['knowledge_name'])
			)
		positions.sort(key=lambda item: item['position_name'])

		return APIResponse.success(
			data={
				'positions': positions,
			},
			message='知识点评分反馈获取成功',
			code=200,
		)


class KnowledgeFeedbackDetailView(APIView):
	permission_classes = [IsAuthenticated]

	@swagger_auto_schema(
		tags=['Recommendation'],
		operation_summary='知识点掌握详情',
		operation_description='返回某个知识点在各次面试中的 logic/accuracy 详情与动态平均分。',
		security=[{'Bearer': []}],
		responses={
			200: openapi.Response('获取成功'),
			401: openapi.Response('未登录'),
			404: openapi.Response('知识点记录不存在'),
		},
	)
	def get(self, request, knowledge_id):
		queryset = UserKnowledgeMatrics.objects.select_related(
			'interview',
			'interview__position',
			'job_knowledge',
		).filter(
			interview__user=request.user,
			job_knowledge_id=knowledge_id,
		)

		records = list(queryset.order_by('-id'))
		if not records:
			return APIResponse.error(message='知识点记录不存在', code=404)

		first = records[0]
		position_name = '未知岗位'
		if first.job_knowledge and first.job_knowledge.job_id:
			position = JobPosition.objects.filter(id=first.job_knowledge.job_id).first()
			if position:
				position_name = position.name

		summary = queryset.aggregate(avg_logic=Avg('logic'), avg_accuracy=Avg('accuracy'))
		interview_names = set()
		detail_items = []
		for row in records:
			interview_label = row.interview.name or ''
			if not interview_label:
				interview_label = f"{row.interview.position.name} 面试"
			interview_names.add(interview_label)
			detail_items.append(
				{
					'interview_name': interview_label,
					'tested_at': row.interview.created_at,
					'logic': row.logic,
					'accuracy': row.accuracy,
				}
			)

		return APIResponse.success(
			data={
				'position_name': position_name,
				'knowledge_name': first.job_knowledge.name,
				'test_count': len(records),
				'interview_count': len(interview_names),
				'avg_logic': round(_safe_float(summary['avg_logic']), 2),
				'avg_accuracy': round(_safe_float(summary['avg_accuracy']), 2),
				'test_details': detail_items,
			},
			message='知识点详情获取成功',
			code=200,
		)
