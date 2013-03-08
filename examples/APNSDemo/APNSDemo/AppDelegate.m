//
//  AppDelegate.m
//  APNSDemo
//
//  Created by Hou Kai on 10/24/12.
//  Copyright (c) 2012 Hou Kai. All rights reserved.
//

#import "AppDelegate.h"

#define APNS_SERVER @"http://127.0.0.1:8080/push/device/"

@interface AppDelegate() {
  @private UILabel *_debug;
  @private UILabel *_tokenLabel;
}
- (void)sendProviderDeviceToken:(NSString *)deviceToken;
@end

@implementation AppDelegate

- (void)dealloc
{
    [_window release];
    [super dealloc];
}

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions
{
    self.window = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease];
    // Override point for customization after application launch.
    self.window.backgroundColor = [UIColor whiteColor];
    [self.window makeKeyAndVisible];
    
    self.window = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease];
    // Override point for customization after application launch.
    self.window.backgroundColor = [UIColor whiteColor];
    [self.window makeKeyAndVisible];
    
    UILabel *label = [[UILabel alloc] initWithFrame:CGRectMake(10, 30, 300, 50)];
    label.font = [UIFont fontWithName:@"AppleGothic" size:20];
    label.text = @"Push Notification";
    
    _tokenLabel = [[UILabel alloc] initWithFrame:CGRectMake(10, 200, 300, 100)];
    [_tokenLabel setLineBreakMode:UILineBreakModeCharacterWrap];
    [_tokenLabel setNumberOfLines:2];
    
    NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
    NSString *deviceToken = [defaults stringForKey:@"deviceToken"];
    if (deviceToken != nil) {
        _tokenLabel.text = deviceToken;
    }
    
    _debug = [[UILabel alloc] initWithFrame:CGRectMake(10, 70, 300, 100)];
    [_debug setLineBreakMode:UILineBreakModeCharacterWrap];
    [_debug setNumberOfLines:0];
    
    [self.window addSubview:label];
    [self.window addSubview:_debug];
    [self.window addSubview:_tokenLabel];
    
    // Register for push notifications
    [application registerForRemoteNotificationTypes:
     UIRemoteNotificationTypeBadge
     | UIRemoteNotificationTypeAlert
     | UIRemoteNotificationTypeSound];
    
    return YES;
}

- (void)application:(UIApplication *)application didRegisterForRemoteNotificationsWithDeviceToken:(NSData *)deviceToken {
    NSString *formatted = [[[[deviceToken description]
                               stringByReplacingOccurrencesOfString:@"<"withString:@""]
                              stringByReplacingOccurrencesOfString:@">" withString:@""]
                             stringByReplacingOccurrencesOfString: @" " withString: @""];
    
    NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
    if ([defaults stringForKey:@"deviceToken"] == nil) {
        [defaults setObject:formatted forKey:@"deviceToken"];
        [defaults synchronize];
    }
    _tokenLabel.text = formatted;
    
    [self sendProviderDeviceToken:formatted];
}

- (void)application:(UIApplication *)application didFailToRegisterForRemoteNotificationsWithError:(NSError *)error {
    if (error.code == 3010) {
        NSLog(@"Push notifications are not supported in the iOS Simulator.");
    } else {
        // show some alert or otherwise handle the failure to register.
        NSLog(@"application:didFailToRegisterForRemoteNotificationsWithError: %@", error);
	}
}

- (void)sendProviderDeviceToken:(NSString *)deviceToken {
    NSLog(@"device token: %@", deviceToken);
    NSMutableData *data = [NSMutableData data];
    NSString *params = [NSString stringWithFormat:@"token=%@", deviceToken];
    [data appendData:[params dataUsingEncoding:NSUTF8StringEncoding]];
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:
                                    [NSURL URLWithString:APNS_SERVER]];
    [request setValue:@"application/x-www-form-urlencoded" forHTTPHeaderField:@"Content-Type"];
    [request setHTTPMethod:@"PUT"];
    [request setHTTPBody:data];
    [NSURLConnection connectionWithRequest:request delegate:self];
}


- (void)connection:(NSURLConnection *)connection didReceiveResponse:(NSURLResponse *)response{
    NSHTTPURLResponse *res = (NSHTTPURLResponse *)response;
	int statusCode = [res statusCode];
    NSString *text = [NSString stringWithFormat:@"SendProviderDeviceToken status code = %d",statusCode];
    _debug.text = text;
}
- (void)connection:(NSURLConnection*)connection didFailWithError:(NSError*)error{
    NSString *text = [NSString stringWithFormat:@"SendProviderDeviceToken error %@",error];
    _debug.text = text;
}

- (void)application:(UIApplication *)application didReceiveRemoteNotification:(NSDictionary *)userInfo {
    _debug.text = [NSString stringWithFormat:@"%@", userInfo];
}

- (void)applicationWillResignActive:(UIApplication *)application
{
    // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
    // Use this method to pause ongoing tasks, disable timers, and throttle down OpenGL ES frame rates. Games should use this method to pause the game.
}

- (void)applicationDidEnterBackground:(UIApplication *)application
{
    // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later. 
    // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
}

- (void)applicationWillEnterForeground:(UIApplication *)application
{
    // Called as part of the transition from the background to the inactive state; here you can undo many of the changes made on entering the background.
}

- (void)applicationDidBecomeActive:(UIApplication *)application
{
    // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
}

- (void)applicationWillTerminate:(UIApplication *)application
{
    // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
}

@end
