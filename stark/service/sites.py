from django.conf.urls import url
from django.shortcuts import HttpResponse,render,redirect
from django.utils.safestring import mark_safe
from django.db.models.fields.related import ManyToManyField
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms import ModelForm

class Show_list(object):

    def __init__(self,config,data_list):
        self.config=config
        self.data_list=data_list

    # 处理表头

    def get_header(self):
        header_list = []
        for field in self.config.new_list_display():
            # field为字符串
            if isinstance(field, str):

                # field为'__str__'时返回类名称大写的字符串形式
                if field == '__str__':
                    val = self.config.model._meta.model_name.upper()
                # 返回类定义时字段的verbose_name
                else:
                    field_obj = self.config.model._meta.get_field(field)
                    val = field_obj.verbose_name
            # field为函数名称时返回函数名称
            else:
                val = field(self, is_header=True)
            header_list.append(val)
        return header_list

    # 处理表单数据

    def get_body(self):
        new_data_list = []
        for obj in self.data_list:
            temp = []
            for field in self.config.new_list_display():
                if isinstance(field, str):
                    try:
                        # 处理多对多字段
                        field_obj = self.config.model._meta.get_field(field)
                        if isinstance(field_obj, ManyToManyField):
                            l = []
                            for i in getattr(obj, field).all():
                                l.append(str(i))
                            val = ','.join(l)
                        # 处理其他字段
                        else:
                            val = getattr(obj, field)
                    except Exception as e:
                        val = getattr(obj, field)
                else:
                    val = field(self, obj)
                temp.append(val)

            new_data_list.append(temp)
        return new_data_list

    #处理action
    def get_new_actions(self):
        action_list=[]
        for i in self.config.actions:
            action_list.append({
                "desc":i.desc,
                "name":i.__name__,
            })

        return action_list


class ModelStark():

    list_display=["__str__",]
    actions=[]
    search_fields=[]


    def __init__(self,model,site):
        self.model=model
        self.site=site

    # 选择框
    def checkbox(self,obj=None,is_header=False):
        if is_header:
            return '选择'
        return mark_safe("<input type='checkbox' name='selected_pk' value=%s>" %obj.pk)

    # 编辑链接
    def edit(self,obj=None,is_header=False):
        # info = self.model._meta.app_label, self.model._meta.model_name
        if is_header:
            return '操作'

        return mark_safe("<a href='change/%s'>编辑</a>"%obj.pk)

        # #反向解析url
        # re_url=reverse('%s/%s/my_change'%info,args=(obj.pk,))
        # # print('re_url',re_url)
        # return mark_safe("<a href='%s'>编辑</a>"%re_url)

    # 删除链接
    def delete(self,obj=None,is_header=False):
        # info = self.model._meta.app_label, self.model._meta.model_name
        if is_header:
            return '操作'
        return mark_safe("<a href='delete/%s'>删除</a>"%obj.pk)

        # re_url=reverse('%s/%s/my_delete'%info,args=(obj.pk,))
        # return mark_safe("<a href='%s'>删除</a>"%re_url)

    # 将通用显示的功能和自定义功能整合到一起
    def new_list_display(self):
        temp=[]
        temp.append(ModelStark.checkbox)
        temp.extend(self.list_display)
        temp.append(ModelStark.edit)
        temp.append(ModelStark.delete)

        return temp

    #查询指定字段
    def get_search_condition(self,request):
        search_condition=Q()
        val=request.GET.get('q')
        if val:
            search_condition.connector="or"

            for field in self.search_fields:
                search_condition.children.append((field+"__contains",val))

        return search_condition

    # 查询功能
    def list_view(self,request):
        if request.method=='POST':
            action=request.POST.get('action')
            selected_pk=request.POST.getlist("selected_pk")

            action=getattr(self,action)
            action(selected_pk)

        search_condition=self.get_search_condition(request)
        data_list=self.model.objects.all().filter(search_condition)
        appName=self.model._meta.app_label
        s1=Show_list(self,data_list)

        return render(request, 'list_view.html', locals())

    def get_list_url(self):
        appName = self.model._meta.app_label
        modelName = self.model._meta.model_name
        _url=reverse("%s/%s/my_listView"%(appName,modelName))

        return _url

    def get_modelForm(self):
        class DemoModelForm(ModelForm):
            class Meta:
                model=self.model
                fields="__all__"

        return DemoModelForm

    #添加功能
    def add(self,request):
        if request.method=='POST':
            form=self.get_modelForm()(request.POST)
            if form.is_valid():
                form.save()
                return redirect(self.get_list_url())
            else:
                return render(request, 'add.html', locals())
        form=self.get_modelForm()()
        return render(request, 'add.html', locals())

    # 编辑
    def change(self,request,id):
        obj=self.model.objects.filter(pk=id).first()
        if request.method=='POST':
            form=self.get_modelForm()(request.POST,instance=obj)
            if form.is_valid():
                form.save()

                return redirect(self.get_list_url())

        form=self.get_modelForm()(instance=obj)
        return render(request, 'change.html', locals())

    #删除
    def delete_view(self,request,id):
        if request.method=='POST':
            self.model.objects.get(pk=id).delete()

            return redirect(self.get_list_url())

        url=self.get_list_url()
        return render(request, 'delete.html', locals())

    def extra_url(self):
        return []

    # 二级分发
    def get_urls2(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        temp=[
            url('^add/$',self.add,name='%s/%s/add'%info),
            url('^$',self.list_view,name='%s/%s/my_listView'%info),
            url('^change/(\d+)/$',self.change,name='%s/%s/my_change'%info),
            url('^delete/(\d+)/$',self.delete_view,name='%s/%s/my_delete'%info),
        ]

        temp.extend(self.extra_url())

        return temp

    @property
    def urls2(self):
        return self.get_urls2(),None,None


class StarkSite():

    def __init__(self,app_D=None):
        self._registry={}

    def get_appD(self,request,label=None):
        # 获取app信息

        app_D = {}
        app_l = []

        if label:
            models={
                m:m_a for m,m_a in self._registry.items() if m._meta.app_label==label
            }
        else:
            models=self._registry

        for model, model_class_obj in models.items():
            app_name = model._meta.app_label
            model_name = model._meta.model_name
            if app_name not in app_D:
                app_l.append(model_name)
                app_D[app_name] = app_l
                app_l=[]
            else:
                new_l=app_D[app_name]
                new_l.append(model_name)


        return app_D

    def index(self,request,label=None):
        # 将获取的app信息展现在首页
        label=label
        app_D=self.get_appD(request,label)

        return render(request, 'index.html', locals())

    def login(self,request):
        return HttpResponse('login')

    def logout(self,request):
        return HttpResponse('logout')

    # 一级分发
    def get_urls(self):

        temp=[
            url(r'^$',self.index,name='index'),
            url(r'^index/(\w+)/$',self.index,name='index'),
            url(r'^login/$',self.login,name='login'),
            url(r'^logout/$',self.logout,name='logout'),
        ]

        for model,model_class_obj in self._registry.items():
            app_name=model._meta.app_label #模型中的类的所属APP的字符串形式的名称
            model_name=model._meta.model_name #模型中的类名称的字符串形式
            temp.append(url(r'%s/%s/'%(app_name,model_name),model_class_obj.urls2))

        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None

    # 注册模型类，如果自定义配置类，则使用自定义配置类，如果未定义，则使用默认配置类ModelStark
    def register(self,model,admin_class=None,**options):
        if not admin_class:
            admin_class=ModelStark

        self._registry[model]=admin_class(model,self)


site=StarkSite()