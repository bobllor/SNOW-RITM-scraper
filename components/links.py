from dataclasses import dataclass

@dataclass
class Links:
    '''
    Class which holds the links used to navigate Service NOW.
    '''
    dashboard: str = 'https://tek.service-now.com/navpage.do'
    vtb: str = 'https://tek.service-now.com/nav_to.do?uri=%2F$vtb.do%3Fsysparm_board%3D43c1517e8780b0d0a6df2f47cebb3523'
    new_user: str = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user.do%3Fsys_id%3D-1%26sys_is_list%3Dtrue%26sys_target%3Dsys_user%26sysparm_checked_items%3D%26sysparm_fixed_query%3D%26sysparm_group_sort%3D%26sysparm_list_css%3D%26sysparm_query%3DGOTO123TEXTQUERY321%3DDavid%2BKvachev%26sysparm_referring_url%3Dsys_user_list.do%3Fsysparm_query%3DGOTO123TEXTQUERY321%253DDavid%2BKvachev@99@sysparm_first_row%3D1%26sysparm_target%3D%26sysparm_view%3D'
    user_link: str = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user_list.do%3Fsysparm_clear_stack%3Dtrue%26sysparm_userpref_module%3D62354a4fc0a801941509bc63f8c4b979'
    
    # related to the new SNOW
    new_dashboard: str = 'https://tek.service-now.com/now/nav/ui/classic/params/target/%24pa_dashboard.do'
    new_vtb: str = 'https://tek.service-now.com/$vtb.do?sysparm_board=43c1517e8780b0d0a6df2f47cebb3523'
    new_user_link: str = 'https://tek.service-now.com/sys_user_list.do?sysparm_clear_stack=true&sysparm_userpref_module=62354a4fc0a801941509bc63f8c4b979'
    new_new_user: str = 'https://tek.service-now.com/sys_user.do?sys_id=-1&sys_is_list=true&sys_target=sys_user&sysparm_checked_items=&sysparm_fixed_query=&sysparm_group_sort=&sysparm_list_css=&sysparm_query=&sysparm_referring_url=sys_user_list.do&sysparm_target=&sysparm_view='