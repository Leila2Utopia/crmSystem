from stark.service.sites import site,ModelStark
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.shortcuts import render
from django.conf.urls import url

from crm import models

site.register(models.UserInfo)
site.register(models.ClassList)

site.register(models.ConsultRecord)
site.register(models.Course)
site.register(models.Customer)
site.register(models.Department)
site.register(models.School)

class ClassStudyRecordConfig(ModelStark):

    def detail(self,obj=None,is_header=False):
        if is_header:
            return '详细信息'
        return mark_safe("<a href='/stark/crm/studentstudyrecord/?class_study_record=%s'>详细信息</a>"%obj.pk)

    def record_score(self,obj=None,is_header=False):
        if is_header:
            return '录入成绩'
        return mark_safe("<a href='record_score/%s'>录入成绩</a>"%obj.pk)

    list_display = ["class_obj",'day_num',detail,record_score]

    def patch_init(self,seleted_pk):
        classstudyrecord_list=self.model.objects.filter(pk__in=seleted_pk)
        for clssstudyrecord in classstudyrecord_list:
            student_list=models.Student.objects.filter(class_list=clssstudyrecord.class_obj)
            for student in student_list:
                models.StudentStudyRecord.objects.create(class_study_record=clssstudyrecord,student=student)

    patch_init.desc='批量初始化'
    actions = [patch_init]

    def record_score(self,request,id):
        csr=models.ClassStudyRecord.objects.get(pk=id)
        student_study_record_list=models.StudentStudyRecord.objects.filter(class_study_record=csr)
        score_choices=models.StudentStudyRecord.score_choices
        update=False
        if request.method=='POST':
            for k,v in request.POST.items():
                if k =='csrfmiddlewaretoken':continue
                field,pk=k.rsplit('_',1)
                dic={field:v}
                models.StudentStudyRecord.objects.filter(pk=pk).update(**dic)

            update=True

        return render(request,'record_score.html',locals())

    def extra_url(self):
        temp=[]
        temp.append(url("record_score/(\d+)",self.record_score))

        return temp

site.register(models.ClassStudyRecord,ClassStudyRecordConfig)

class StudentConfig(ModelStark):

    def display_score(self,obj=None,is_header=False):
        if is_header:
            return '个人成绩'
        return mark_safe("<a href='score/%s'>个人成绩</a>"%obj.pk)

    list_display = ['customer','class_list',display_score]

    def score(self,request,sid):

        if request.is_ajax():
            cid=request.GET.get('cid')
            sid=request.GET.get('sid')

            ret=student_study_record_list=list(models.StudentStudyRecord.objects.filter(student_id=sid,class_study_record__class_obj_id=cid).values_list("class_study_record__day_num",'score'))
            ret=[['day'+str(i[0]),i[1]] for i in ret]
            return JsonResponse(ret,safe=False)

        student=models.Student.objects.get(pk=sid)
        class_list=student.class_list.all()

        return render(request, 'score.html', locals())

    def extra_url(self):
        temp=[]
        temp.append(url("score/(\d+)",self.score))
        return temp

site.register(models.Student,StudentConfig)

class StudentStudyRecordConfig(ModelStark):

    def display_record(self,obj=None,is_header=False):
        if is_header:
            return '考勤'
        return obj.get_record_display()

    def display_score(self,obj=None,is_header=False):
        if is_header:
            return '成绩'
        return obj.get_score_display()

    list_display = ['student', "class_study_record", display_record, display_score]

    def patch_late(self,selected_pk):
        self.model.objects.filter(pk__in=selected_pk).update(record='late')

    patch_late.desc='迟到'
    actions = [patch_late]

site.register(models.StudentStudyRecord,StudentStudyRecordConfig)

